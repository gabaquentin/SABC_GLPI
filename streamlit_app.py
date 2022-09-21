import pandas as pd
import streamlit as st

st.title("Hi Anber! Welcome to Streamlit!")

st.write("My first DataFrame")

st.write(
    pd.DataFrame({
        'A': [1, 5, 9, 7],
        'B': [3, 2, 4, 8]
    })
)