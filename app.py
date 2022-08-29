import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st


# Set Streamlit config
st.set_page_config(
    page_title="Etude du CA",
    page_icon=":bar_chart:",
)

uploaded_file = st.file_uploader("Please upload a file", type="csv")
start_year, end_year = 2020, 2021
first_order_columns = ["Q", "F", "P"]


if uploaded_file is not None:
    user_df = pd.read_csv(uploaded_file, index_col=("Year", "Reference", "Currency"))

    user_df_by_year = lambda year: user_df[user_df.index.get_level_values('Year').isin([year])]
    CA = lambda year: user_df_by_year(year)[first_order_columns].product(axis=1).sum()

    df_start = user_df_by_year(start_year).droplevel("Year")
    difference_end_minus_start = (user_df_by_year(end_year).droplevel("Year") - df_start).rename(columns=lambda x: 'd' + x)
    start_and_difference = pd.concat((df_start, difference_end_minus_start), axis=1)

    k = lambda x: [bool(x & (1 << y)) * 'd' + l for y, l in enumerate(first_order_columns)]

    dvp = {"".join(k(x)): start_and_difference[k(x)].product(axis=1) for x in range(1 << len(first_order_columns))}
    balance = dvp["dQdFdP"] + dvp["dQdFP"] + dvp["dQFdP"] + dvp["QdFdP"]
    # qte = dvp["dQFP"]
    price_effect = dvp["QFdP"]
    currency_effect = dvp["QdFP"]
    gq = user_df_by_year(end_year)["Q"].sum() / user_df_by_year(start_year)["Q"].sum() - 1
    Qtilde = (1 + gq) * start_and_difference["Q"]
    mix_effect = (user_df_by_year(end_year).droplevel("Year")["Q"] - Qtilde) * start_and_difference["F"] * start_and_difference["P"]
    volume_difference = (Qtilde - start_and_difference["Q"]) * start_and_difference["F"] * start_and_difference["P"]

    rst = np.array(
    [CA(start_year), price_effect.sum(), currency_effect.sum(), volume_difference.sum(), mix_effect.sum(), balance.sum(), CA(end_year)]
)

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.bar(
        np.arange(len(rst)),
        rst,
        bottom=[0] + list(np.cumsum(rst)[:-2]) + [0],
        color=['gray', *('red' if e < 0 else 'green' for e in rst[1: -1]), 'gray'],
        tick_label=[f"CA_{start_year}", "Prix", "Devise", "Volume", "Mix", "Croisé", f"CA_{end_year}"]
    )
    ax.set_title(f"Décomposition du Chiffre d'Affaires\nentre l'année {start_year} et l'année {end_year}")
    ax.set_xlabel("Effets")
    ax.set_ylabel("Montant (€)")
    st.pyplot(fig)
