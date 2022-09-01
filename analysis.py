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
    col1, col2 = st.columns(2)
    # Get starting and final years
    start_year = col1.number_input("Initial year", min_year, max_year - 1)
    end_year = col2.number_input("End year", int(start_year + 1), max_year)
    # Get booleans to show mix effects
    quantity_effect_split = col1.checkbox("Show mix effect for quantities", True)
    price_effect_split = col2.checkbox("Show mix effect for prices", True)
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
    # fig = plt.figure()
    # ax = fig.add_subplot(111)
    # ax.bar(
    #     np.arange(len(final_array_to_plot)),
    #     final_array_to_plot,
    #     bottom=bottom,
    #     color=color,
    #     tick_label=ticks
    # )
    # ax.set_title(f"Décomposition du Chiffre d'Affaires\nentre l'année {start_year} et l'année {end_year}")
    # # ax.set_xlabel("Effets")
    # ax.set_ylabel("Montant (€)")

    # _, col_plot, _ = st.columns([1, 2, 1])
    # col_plot.pyplot(fig)

    source = alt.pd.DataFrame([
        {
            "question": "Question 1",
            "type": "Strongly disagree",
            "value": 24,
            "percentage": 0.7,
            "percentage_start": -19.1,
            "percentage_end": -18.4
        },
        {
            "question": "Question 1",
            "type": "Disagree",
            "value": 294,
            "percentage": 9.1,
            "percentage_start": -18.4,
            "percentage_end": -9.2
        },
        {
            "question": "Question 1",
            "type": "Neither agree nor disagree",
            "value": 594,
            "percentage": 18.5,
            "percentage_start": -9.2,
            "percentage_end": 9.2
        },
        {
            "question": "Question 1",
            "type": "Agree",
            "value": 1927,
            "percentage": 59.9,
            "percentage_start": 9.2,
            "percentage_end": 69.2
        },
        {
            "question": "Question 1",
            "type": "Strongly agree",
            "value": 376,
            "percentage": 11.7,
            "percentage_start": 69.2,
            "percentage_end": 80.9
        },

        {
            "question": "Question 2",
            "type": "Strongly disagree",
            "value": 2,
            "percentage": 18.2,
            "percentage_start": -36.4,
            "percentage_end": -18.2
        },
        {
            "question": "Question 2",
            "type": "Disagree",
            "value": 2,
            "percentage": 18.2,
            "percentage_start": -18.2,
            "percentage_end": 0
        },
        {
            "question": "Question 2",
            "type": "Neither agree nor disagree",
            "value": 0,
            "percentage": 0,
            "percentage_start": 0,
            "percentage_end": 0
        },
        {
            "question": "Question 2",
            "type": "Agree",
            "value": 7,
            "percentage": 63.6,
            "percentage_start": 0,
            "percentage_end": 63.6
        },
        {
            "question": "Question 2",
            "type": "Strongly agree",
            "value": 11,
            "percentage": 0,
            "percentage_start": 63.6,
            "percentage_end": 63.6
        },

        {
            "question": "Question 3",
            "type": "Strongly disagree",
            "value": 2,
            "percentage": 20,
            "percentage_start": -30,
            "percentage_end": -10
        },
        {
            "question": "Question 3",
            "type": "Disagree",
            "value": 0,
            "percentage": 0,
            "percentage_start": -10,
            "percentage_end": -10
        },
        {
            "question": "Question 3",
            "type": "Neither agree nor disagree",
            "value": 2,
            "percentage": 20,
            "percentage_start": -10,
            "percentage_end": 10
        },
        {
            "question": "Question 3",
            "type": "Agree",
            "value": 4,
            "percentage": 40,
            "percentage_start": 10,
            "percentage_end": 50
        },
        {
            "question": "Question 3",
            "type": "Strongly agree",
            "value": 2,
            "percentage": 20,
            "percentage_start": 50,
            "percentage_end": 70
        },

        {
            "question": "Question 4",
            "type": "Strongly disagree",
            "value": 0,
            "percentage": 0,
            "percentage_start": -15.6,
            "percentage_end": -15.6
        },
        {
            "question": "Question 4",
            "type": "Disagree",
            "value": 2,
            "percentage": 12.5,
            "percentage_start": -15.6,
            "percentage_end": -3.1
        },
        {
            "question": "Question 4",
            "type": "Neither agree nor disagree",
            "value": 1,
            "percentage": 6.3,
            "percentage_start": -3.1,
            "percentage_end": 3.1
        },
        {
            "question": "Question 4",
            "type": "Agree",
            "value": 7,
            "percentage": 43.8,
            "percentage_start": 3.1,
            "percentage_end": 46.9
        },
        {
            "question": "Question 4",
            "type": "Strongly agree",
            "value": 6,
            "percentage": 37.5,
            "percentage_start": 46.9,
            "percentage_end": 84.4
        },

        {
            "question": "Question 5",
            "type": "Strongly disagree",
            "value": 0,
            "percentage": 0,
            "percentage_start": -10.4,
            "percentage_end": -10.4
        },
        {
            "question": "Question 5",
            "type": "Disagree",
            "value": 1,
            "percentage": 4.2,
            "percentage_start": -10.4,
            "percentage_end": -6.3
        },
        {
            "question": "Question 5",
            "type": "Neither agree nor disagree",
            "value": 3,
            "percentage": 12.5,
            "percentage_start": -6.3,
            "percentage_end": 6.3
        },
        {
            "question": "Question 5",
            "type": "Agree",
            "value": 16,
            "percentage": 66.7,
            "percentage_start": 6.3,
            "percentage_end": 72.9
        },
        {
            "question": "Question 5",
            "type": "Strongly agree",
            "value": 4,
            "percentage": 16.7,
            "percentage_start": 72.9,
            "percentage_end": 89.6
        },

        {
            "question": "Question 6",
            "type": "Strongly disagree",
            "value": 1,
            "percentage": 6.3,
            "percentage_start": -18.8,
            "percentage_end": -12.5
        },
        {
            "question": "Question 6",
            "type": "Disagree",
            "value": 1,
            "percentage": 6.3,
            "percentage_start": -12.5,
            "percentage_end": -6.3
        },
        {
            "question": "Question 6",
            "type": "Neither agree nor disagree",
            "value": 2,
            "percentage": 12.5,
            "percentage_start": -6.3,
            "percentage_end": 6.3
        },
        {
            "question": "Question 6",
            "type": "Agree",
            "value": 9,
            "percentage": 56.3,
            "percentage_start": 6.3,
            "percentage_end": 62.5
        },
        {
            "question": "Question 6",
            "type": "Strongly agree",
            "value": 3,
            "percentage": 18.8,
            "percentage_start": 62.5,
            "percentage_end": 81.3
        },

        {
            "question": "Question 7",
            "type": "Strongly disagree",
            "value": 0,
            "percentage": 0,
            "percentage_start": -10,
            "percentage_end": -10
        },
        {
            "question": "Question 7",
            "type": "Disagree",
            "value": 0,
            "percentage": 0,
            "percentage_start": -10,
            "percentage_end": -10
        },
        {
            "question": "Question 7",
            "type": "Neither agree nor disagree",
            "value": 1,
            "percentage": 20,
            "percentage_start": -10,
            "percentage_end": 10
        },
        {
            "question": "Question 7",
            "type": "Agree",
            "value": 4,
            "percentage": 80,
            "percentage_start": 10,
            "percentage_end": 90
        },
        {
            "question": "Question 7",
            "type": "Strongly agree",
            "value": 0,
            "percentage": 0,
            "percentage_start": 90,
            "percentage_end": 90
        },

        {
            "question": "Question 8",
            "type": "Strongly disagree",
            "value": 0,
            "percentage": 0,
            "percentage_start": 0,
            "percentage_end": 0
        },
        {
            "question": "Question 8",
            "type": "Disagree",
            "value": 0,
            "percentage": 0,
            "percentage_start": 0,
            "percentage_end": 0
        },
        {
            "question": "Question 8",
            "type": "Neither agree nor disagree",
            "value": 0,
            "percentage": 0,
            "percentage_start": 0,
            "percentage_end": 0
        },
        {
            "question": "Question 8",
            "type": "Agree",
            "value": 0,
            "percentage": 0,
            "percentage_start": 0,
            "percentage_end": 0
        },
        {
            "question": "Question 8",
            "type": "Strongly agree",
            "value": 2,
            "percentage": 100,
            "percentage_start": 0,
            "percentage_end": 100
        }
    ])

    color_scale = alt.Scale(
        domain=[
            "Strongly disagree",
            "Disagree",
            "Neither agree nor disagree",
            "Agree",
            "Strongly agree"
        ],
        range=["#c30d24", "#f3a583", "#cccccc", "#94c6da", "#1770ab"]
    )

    y_axis = alt.Axis(
        title='Question',
        offset=5,
        ticks=False,
        minExtent=60,
        domain=False
    )

    c = alt.Chart(source).mark_bar().encode(
        x='percentage_start:Q',
        x2='percentage_end:Q',
        y=alt.Y('question:N', axis=y_axis),
        color=alt.Color(
            'type:N',
            legend=alt.Legend( title='Response'),
            scale=color_scale,
        )
    )

    st.altair_chart(c, use_container_width=True)
