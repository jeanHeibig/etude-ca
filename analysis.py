import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st


def main(sales_file, fx_file):
    sales_df = pd.read_csv(sales_file, index_col=("Year", "Reference", "Currency")).rename(columns={"Quantity": "Q", "Price": "P"})

    col1, col2 = st.columns(2)

    first_order_columns = ["Q", "F", "P"]
    dvp_indices = lambda x: [bool(x & (1 << y)) * 'd' + l for y, l in enumerate(first_order_columns)]

    min_year = int(sales_df.index.get_level_values("Year").min())
    max_year = int(sales_df.index.get_level_values("Year").max())

    start_year = col1.number_input("Initial year", min_year, max_year - 1)
    end_year = col2.number_input("End year", int(start_year + 1), max_year)
    quantity_effect_split = col1.checkbox("Show mix q effect", False)
    price_effect_split = col2.checkbox("Show mix p effect", False)

    fx_rate = pd.read_csv(fx_file, index_col="Year")

    sales_df_by_year = lambda year: sales_df[sales_df.index.get_level_values('Year').isin([year])]

    grouped_start = sales_df_by_year(start_year).droplevel("Year").groupby(["Reference", "Currency"]).agg({"P": "mean", "Q": "sum"})
    grouped_end = sales_df_by_year(end_year).droplevel("Year").groupby(["Reference", "Currency"]).agg({"P": "mean", "Q": "sum"})
    merged_start_and_end = pd.merge(grouped_start, grouped_end, 'outer', on=["Reference", "Currency"], suffixes=("", "_end"))

    merged_currencies = pd.merge(merged_start_and_end, fx_rate.T[[start_year, end_year]], how="left", left_on="Currency", right_index=True).rename(columns={start_year: "F", end_year: "F_end"})

    filled_start_and_end = merged_currencies.fillna({"P_end": merged_currencies["P"], "Q_end": 0, "P": merged_currencies["P_end"], "Q": 0})

    df_start = filled_start_and_end[first_order_columns]
    df_end = filled_start_and_end[[c + "_end" for c in first_order_columns]].rename(columns=lambda x: x[0])

    CA_start = df_start[first_order_columns].product(axis=1).sum()
    CA_end = df_end[first_order_columns].product(axis=1).sum()

    difference = (df_end - df_start).rename(columns=lambda x: 'd' + x)
    start_and_difference = pd.concat((df_start, difference), axis=1)

    developped_product = {"".join(dvp_indices(x)): start_and_difference[dvp_indices(x)].product(axis=1) for x in range(1 << len(first_order_columns))}
    balance = developped_product["dQdFdP"] + developped_product["dQdFP"] + developped_product["dQFdP"] + developped_product["QdFdP"]
    quantity_effect = developped_product["dQFP"]
    price_effect = developped_product["QFdP"]
    currency_effect = developped_product["QdFP"]
    volume_start = df_start["Q"].sum()
    growth_quantities = (df_end["Q"] / df_start["Q"] * df_start["Q"]).sum() / volume_start - 1 if volume_start else 0
    adjusted_quantities = (1 + growth_quantities) * df_start["Q"] if volume_start else df_end["Q"]
    mix_quantity_effect = (df_end["Q"] - adjusted_quantities) * df_start["F"] * df_start["P"]
    volume_difference = (adjusted_quantities - df_start["Q"]) * df_start["F"] * df_start["P"]

    growth_prices = (df_end["P"] / df_start["P"] * df_start["Q"]).sum() / volume_start - 1 if volume_start else 0
    adjusted_prices = (1 + growth_prices) * df_start["P"] if volume_start else df_end["P"]
    mix_price_effect = (df_end["P"] - adjusted_prices) * df_start["F"] * df_start["Q"]
    inflation = (adjusted_prices - df_start["P"]) * df_start["F"] * df_start["Q"]

    effect_values = {
        "price": price_effect.sum(),
        "currency": currency_effect.sum(),
        "volume": volume_difference.sum(),
        "mix q": mix_quantity_effect.sum(),
        "quantity": quantity_effect.sum(),
        "mix p": mix_price_effect.sum(),
        "inflation": inflation.sum(),
        "balance": balance.sum()
    }
    effect_ticks = {
        "price": "Prix",
        "currency": "Devise",
        "volume": "Volume",
        "mix q": "Mix Q",
        "quantity": "Quantité",
        "mix p": "Mix P",
        "inflation": "Inflation",
        "balance": "Croisé"
    }
    selected_effects = [*(["inflation", "mix p"] if price_effect_split else ["price"]), "currency", *(["volume", "mix q"] if quantity_effect_split else ["quantity"]), "balance"]
    final_array_to_plot = np.array([CA_start, *[effect_values[effect] for effect in selected_effects], CA_end])
    ticks = [f"$CA_{{{start_year}}}$", *[effect_ticks[effect] for effect in selected_effects], f"$CA_{{{end_year}}}$"]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.bar(
        np.arange(len(final_array_to_plot)),
        final_array_to_plot,
        bottom=[0] + list(np.cumsum(final_array_to_plot)[:-2]) + [0],
        color=['gray', *('red' if e < 0 else 'green' for e in final_array_to_plot[1: -1]), 'gray'],
        tick_label=ticks
    )
    ax.set_title(f"Décomposition du Chiffre d'Affaires\nentre l'année {start_year} et l'année {end_year}")
    ax.set_xlabel("Effets")
    ax.set_ylabel("Montant (€)")
    st.pyplot(fig)