import altair as alt
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st


def main(sales_file, fx_file):
    # Load inputs into two pandas DataFrames
    sales_df = pd.read_csv(sales_file, index_col=("Year", "Reference", "Currency")).rename(columns={"Quantity": "Q", "Price": "P"})
    fx_rate = pd.read_csv(fx_file, index_col="Year")

    # Get min and max years
    min_year = int(sales_df.index.get_level_values("Year").min())
    max_year = int(sales_df.index.get_level_values("Year").max())

    # Set two columns for Streamlit
    col1, col2, col3 = st.columns([1, 1, 4])
    # Get starting and final years
    start_year = col1.number_input("Année initiale", min_year, max_year - 1)
    end_year = col2.number_input("Année finale", int(start_year + 1), max_year)
    # Get booleans to show mix effects
    quantity_effect_split = col1.checkbox("Afficher l'effet mix des quantités", True)
    price_effect_split = col2.checkbox("Afficher l'effet mix des prix", True)
    # Deduce the selected effects given user's inputs
    selected_effects = [*(["inflation_effect", "mix p"] if price_effect_split else ["price"]), "currency", *(["volume", "mix q"] if quantity_effect_split else ["quantity"]), "compensation_term"]

    # Filter the data to keep only relevant years
    sales_df_by_year = lambda year: sales_df[sales_df.index.get_level_values('Year').isin([year])]
    grouped_start = sales_df_by_year(start_year).droplevel("Year").groupby(["Reference", "Currency"]).agg({"P": "mean", "Q": "sum"})
    grouped_end = sales_df_by_year(end_year).droplevel("Year").groupby(["Reference", "Currency"]).agg({"P": "mean", "Q": "sum"})
    # Now merge both DataFrames
    right_suffix = "_end"  # Suffix used to distinguish the final year
    # Use an `outer` merge in order to keep items added and removed from one year to another
    both_years = pd.merge(grouped_start, grouped_end, 'outer', on=["Reference", "Currency"], suffixes=("", right_suffix))
    
    # Merge the currencies from the given input file
    merged_currencies = pd.merge(both_years, fx_rate.T[[start_year, end_year]], how="left", left_on="Currency", right_index=True).rename(columns={start_year: "F", end_year: "F" + right_suffix})

    # Fill missing values (ie. for additions & suppresions of products)
    # Values are taken from the other year
    # TODO: Add a correction for inflation_effect & volume effects
    filled_missing_values = merged_currencies.fillna({"P" + right_suffix: merged_currencies["P"], "Q" + right_suffix: 0, "P": merged_currencies["P" + right_suffix], "Q": 0})

    # Now looking to compute the differences between starting and final years
    # Generate all 2^k string indices for the developped product from ["Q", "F", "P"] to ["dQ", "dF", "dP"]
    list_indices = lambda x: [bool(x & (1 << y)) * 'd' + l for y, l in enumerate(["Q", "F", "P"])]  # As a list
    str_indices = lambda x: "".join(list_indices(x))  # As a string for column names
    # Get strarting and final DataFrames (differ from above DataFrames as here there are filled values and currencies)
    df_start = filled_missing_values[list_indices(0)]
    df_end = filled_missing_values[[c + right_suffix for c in list_indices(0)]].rename(columns=lambda x: x[0])

    # Create a DataFrame with starting values and differences
    difference = pd.concat((df_start, (df_end - df_start).rename(columns=lambda x: 'd' + x)), axis=1)
    # Compute all terms of the final year in terms of starting year and difference
    developped_product = {str_indices(x): difference[list_indices(x)].product(axis=1) for x in range(1 << len(list_indices(0)))}
    
    # Compute net sales for both years
    net_sales_start = df_start[list_indices(0)].product(axis=1).sum()
    net_sales_end = df_end[list_indices(0)].product(axis=1).sum()

    # Get different effects
    quantity_effect = developped_product["dQFP"]  # First order in Q
    currency_effect = developped_product["QdFP"]  #First order in F
    price_effect = developped_product["QFdP"] # First order in P
    # Second order and above (compensation term)
    compensation_term = developped_product["dQdFdP"] + developped_product["dQdFP"] + developped_product["dQFdP"] + developped_product["QdFdP"]

    # Compute mix effects
    volume_start = df_start["Q"].sum()  # Get the starting volume
    # Get the growth of a given column (quantity or price)
    growth = lambda c: (df_end[c] / df_start[c] * df_start["Q"]).sum() / volume_start - 1 if volume_start else 0
    # Get the updated starting columns with mean increase
    average_increase = lambda c: (1 + growth(c)) * df_start[c] if volume_start else df_end[c]

    # Get mix effect for quantities
    adjusted_quantities = average_increase("Q")
    mix_quantity_effect = (df_end["Q"] - adjusted_quantities) * df_start["F"] * df_start["P"]
    volume_effect = (adjusted_quantities - df_start["Q"]) * df_start["F"] * df_start["P"]

    # Get mix effect for prices
    adjusted_prices = average_increase("P")
    mix_price_effect = (df_end["P"] - adjusted_prices) * df_start["F"] * df_start["Q"]
    inflation_effect = (adjusted_prices - df_start["P"]) * df_start["F"] * df_start["Q"]

    # Compute the sum of all effects
    effect_values = {
        "price": price_effect.sum(),
        "currency": currency_effect.sum(),
        "volume": volume_effect.sum(),
        "mix q": mix_quantity_effect.sum(),
        "quantity": quantity_effect.sum(),
        "mix p": mix_price_effect.sum(),
        "inflation_effect": inflation_effect.sum(),
        "compensation_term": compensation_term.sum()
    }

    # Ticks used for display
    effect_ticks = {
        "price": "Prix",
        "currency": "Devise",
        "volume": "Volume",
        "mix q": "Mix Q",
        "quantity": "Quantité",
        "mix p": "Mix P",
        "inflation_effect": "Inflation",
        "compensation_term": "Croisé"
    }

    # Create an array with desired effects to plot them
    final_array_to_plot = np.array([net_sales_start, *[effect_values[effect] for effect in selected_effects], net_sales_end])
    ticks = [f"$CA_{{{start_year}}}$", *[effect_ticks[effect] for effect in selected_effects], f"$CA_{{{end_year}}}$"]

    # Create the figure
    bottom = [0] + list(np.cumsum(final_array_to_plot)[:-2]) + [0]  # Cumsum baseline
    color = ['gray', *('red' if e < 0 else 'green' for e in final_array_to_plot[1: -1]), 'gray']  # Gray for net sales, green for profits and red for losses
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.bar(
        np.arange(len(final_array_to_plot)),
        final_array_to_plot,
        bottom=bottom,
        color=color,
        tick_label=ticks
    )
    ax.set_title(f"Décomposition du Chiffre d'Affaires\nentre l'année {start_year} et l'année {end_year}")
    # ax.set_xlabel("Effets")
    ax.set_ylabel("Montant (€)")

    col3.pyplot(fig)
