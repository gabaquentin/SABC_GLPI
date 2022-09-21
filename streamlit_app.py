import os
import pathlib
from io import StringIO

import pandas as pd
import streamlit as st

st.title("Validation de la semantique")
st.subheader("Televersez le fichier contenant les données que vous souhaitez valider")


uploaded_file = st.file_uploader("Choisir un fichier csv")

if uploaded_file is not None:
    bytes_data = uploaded_file.getvalue()

    data = uploaded_file.getvalue().decode('utf-8').splitlines()
    st.session_state["preview"] = ''
    for i in range(0, min(5, len(data))):
        st.session_state["preview"] += data[i]

preview = st.text_area("CSV Preview", "", height=150, key="preview")
upload_state = st.text_area("Upload State", "", key="upload_state")


def upload():
    if uploaded_file is None:
        st.session_state["upload_state"] = "Selectionez d'abord le fichier!"
    else:
        data = uploaded_file.getvalue().decode('utf-8')
        parent_path = pathlib.Path(__file__).parent.parent.resolve()
        save_path = os.path.join(parent_path, "data")
        complete_name = os.path.join(save_path, uploaded_file.name)
        destination_file = open(complete_name, "w")
        destination_file.write(data)
        destination_file.close()
        st.session_state["upload_state"] = "Sauvegardé " + complete_name + " avec succés!"
st.button("Soumetre le fichier", on_click=upload)