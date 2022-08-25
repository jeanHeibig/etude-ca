import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st


# Set Streamlit config
st.set_page_config(
    page_title="Etude du CA",
    page_icon=":bar_chart:",
)

uploaded_file = st.file_uploader("Choose a file", type="csv")


def df_prod(df, *c):
    if c:
        return df[c[0]] * df_prod(df, *c[1:])
    else:
        return 1

df = lambda year: user_df[user_df.index.get_level_values('Year').isin([year])]
CA = lambda year: df_prod(df(year), "Q", "F", "P").sum()
ltr = "Q", "F", "P"
k = lambda x: [bool(x & (1 << y)) * 'd' + l for y, l in enumerate(ltr)]

if uploaded_file is not None:
    # Can be used wherever a "file-like" object is accepted:
    user_df = pd.read_csv(uploaded_file, index_col=("Year", "Reference", "Currency"))
    st.dataframe(user_df)

    i, f = 2020, 2021
    dfi = df(i).droplevel("Year")
    d = (df(f).droplevel("Year") - dfi).rename(columns=lambda x: 'd' + x)
    r = pd.concat((dfi, d), axis=1)
    dvp = {"".join(k(x)): df_prod(r, *k(x)) for x in range(1 << len(ltr))}
    balance = dvp["dQdFdP"] + dvp["dQdFP"] + dvp["dQFdP"] + dvp["QdFdP"]
    qte = dvp["dQFP"]
    prix = dvp["QFdP"]
    chg = dvp["QdFP"]
    gq = df(f)["Q"].sum() / df(i)["Q"].sum() - 1
    Qtilde = (1 + gq) * r["Q"]
    mix = (df(f).droplevel("Year")["Q"] - Qtilde) * r["F"] * r["P"]
    vol = (Qtilde - r["Q"]) * r["F"] * r["P"]

    rst = np.array(
    [CA(i), prix.sum(), chg.sum(), vol.sum(), mix.sum(), balance.sum(), CA(f)]
)

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.bar(
        np.arange(len(rst)),
        rst,
        bottom=[0] + list(np.cumsum(rst)[:-2]) + [0],
        color=['gray', *('red' if e < 0 else 'green' for e in rst[1: -1]), 'gray'],
        tick_label=[f"CA_{i}", "Prix", "Devise", "Volume", "Mix", "Croisé", f"CA_{f}"]
    )
    ax.set_title(f"Décomposition du Chiffre d'Affaires\nentre l'année {i} et l'année {f}")
    ax.set_xlabel("Effets")
    ax.set_ylabel("Montant (€)")
    st.pyplot(fig)
