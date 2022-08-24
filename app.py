import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


uploaded_file = st.file_uploader("Choose a file", type="csv", accept_multiple_files=False, key=None, help=None, on_change=None, args=None, kwargs=None, *, disabled=False)

if uploaded_file is not None:
    # Can be used wherever a "file-like" object is accepted:
    dataframe = pd.read_csv(uploaded_file)
    st.dataframe(dataframe)