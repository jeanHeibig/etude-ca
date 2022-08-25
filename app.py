import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


# Set Streamlit config
st.set_page_config(
    page_title="Etude du CA",
    page_icon=":bar_chart:",
)

uploaded_file = st.file_uploader("Choose a file", type="csv")

if uploaded_file is not None:
    # Can be used wherever a "file-like" object is accepted:
    user_df = pd.read_csv(uploaded_file)
    st.dataframe(user_df)
