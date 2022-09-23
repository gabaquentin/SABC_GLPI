#Import the required Libraries

import threading
import time
from os.path import exists

import streamlit as st
import pandas as pd

import subprocess

st.set_page_config(layout="wide")

# Get all data function
def get_data(data, this, fo_r):
    #Load dataframe
    columns = ["Catégorie", this]
    renamed_columns = ["Catégorie", fo_r]

    df = pd.read_csv(data, sep=';')[columns]

    #Rename documents title

    columns_to_rename = {}

    for index, column in enumerate(columns):
        columns_to_rename[column] = renamed_columns[index]
    df = df.rename(columns=columns_to_rename)

    #Drop NaN Fields
    df = df.dropna(axis=0)

    return df

def get_cleaned_cat(df, for_r):
    #CAT Categorie

    all_cat = []
    for cat in df.groupby('Catégorie')[for_r].apply(list).index:
        result_str = ""
        for i in range(0, len(cat)):
            if cat[i] == '>' or cat[i] == '_' or cat[i] == '.' or cat[i] == ' ':
                break
            else:
                result_str = result_str + cat[i]
        all_cat.append(result_str)

    return all_cat

#Subprocess call
def PopenCall(onExit, PopenArgs):
    def runInThread(onExit, PopenArgs):
        script_ID = PopenArgs[1]
        proc = subprocess.Popen(PopenArgs)
        proc.wait()
        onExit(script_ID)
        return

    thread = threading.Thread(target=runInThread, args=(onExit, PopenArgs))
    thread.start()

    return thread

def onExit(script_ID):
    st.write("Done processing", script_ID + ".")

#get dataframe categorized
def get_cat_data(uploaded_file, fo_r, this):
    data_path = ''
    if fo_r == 'Diagnostic':
        data_path = './data/diagnostic'
    elif fo_r == 'Action':
        data_path = './data/action'

    file_exists = exists('{}/{}'.format(data_path, uploaded_file.name))

    if file_exists:
        return pd.read_csv("{}/{}".format(data_path, uploaded_file.name))

    else:
        #Premierement, on vas categoriser les diagnostics, car un bon diagnostic doit pouvoir appartenir a sa categorie d'origine
        df = get_data(uploaded_file, this, fo_r)
        df_to_predict = pd.DataFrame({'Description' : []})
        df_to_predict['Description'] = df[fo_r]

        saved_file_name = time.time()
        df_to_predict.to_csv("{}/file_name_{}.csv".format(data_path, saved_file_name), index=False)

        PopenArgs = [
            "python",
            "./scripts/datarobot-predict.py",
            "{}/file_name_{}.csv".format(data_path, saved_file_name),
            "{}/predicted_file_name_{}.csv".format(data_path, saved_file_name)
        ]
        print ("Running {} in background.......".format(PopenArgs))
        job_thread = PopenCall(onExit, PopenArgs)
        job_thread.join()

        predicted_df = pd.read_csv("{}/predicted_file_name_{}.csv".format(data_path, saved_file_name))

        all_cat = get_cleaned_cat(df, fo_r)

        for cat in all_cat:
            df.loc[df['Catégorie'].str.contains(cat), 'clean_categorie'] = cat

        df['predicted_categorie'] = predicted_df['clean_categorie_PREDICTION']

        df.to_csv("{}/{}".format(data_path, uploaded_file.name), index=False)

        return df

#process validation function
def process_val(df, fo_r, uploaded_file):
    data_path = ''
    if fo_r == 'Diagnostic':
        data_path = './data/diagnostic'
    elif fo_r == 'Action':
        data_path = './data/action'

    valid_exists = exists('{}/valid_{}'.format(data_path, uploaded_file.name))
    invalid_exists = exists('{}/invalid_{}'.format(data_path, uploaded_file.name))

    if valid_exists and invalid_exists:
        return [pd.read_csv("{}/valid_{}".format(data_path, uploaded_file.name)), pd.read_csv("{}/invalid_{}".format(data_path, uploaded_file.name))]
    else:
        df['valid_sentence'] = df[fo_r].apply(validateSentence)
        valid_df = df[df['valid_sentence'] == True]
        invalid_df = df[df['valid_sentence'] == False]

        valid_df = valid_df[valid_df['clean_categorie'] == valid_df['predicted_categorie']]

        invalid_df.append(valid_df[valid_df['clean_categorie'] != valid_df['predicted_categorie']], ignore_index=True)

        valid_df.to_csv("{}/valid_{}".format(data_path, uploaded_file.name), index=False)
        invalid_df.to_csv("{}/invalid_{}".format(data_path, uploaded_file.name), index=False)

        return [valid_df, invalid_df]

# sentences validations functions
def validateSentence(s):
    index = 0
    if s[index].islower():                                # 1er état
        return False

    while index < len(s):
        if s[index].isupper():
            if s[index + 1].isupper():                    # 5ème état
                return False
            if index - 1 >= 0 and s[index - 1] != ' ':    # 2ème état
                return False
        if s[index] == ' ' and s[index + 1] == ' ':     # 4ème état
            return False
        index = index + 1

    if s[index - 2] == ' ' or s[index - 1] != '.':      # 3e état
        return False

    return True

# Functions for each of the pages
def home(uploaded_file):
    if uploaded_file:
        st.header('Verifiez qu\'il s\'agissent bien du bon fichier')
        st.text('Une fois le fichier verifié, vous cliquez sur une option dans le menu de navigation a ⬅️ gauche pour obtenir un 📊 recapitulatif de la validation de la semantique des données des saisient')
        df = pd.read_csv(upload_file, sep=';')
        st.write(df)
    else:
        st.header('Téléverser un fichier pour commencer')

def diagnostics(uploaded_file):
    if uploaded_file:
        st.header('DIAGNOSTICS')
        df = get_cat_data(uploaded_file, 'Diagnostic', 'Diagnostic Intervenant - Description')
        valid_df = process_val(df, 'Diagnostic', uploaded_file)[0]
        invalid_df = process_val(df, 'Diagnostic', uploaded_file)[1]
        st.write(valid_df)
        st.write(invalid_df)
    else:
        home(upload_file)

def actions_menees(uploaded_file):
    if uploaded_file:
        st.header('ACTIONS MENÉES')
        df = get_cat_data(uploaded_file, 'Action', 'Action(s) menée(s) - Action(s) menée(s)')
        valid_df = process_val(df, 'Action', uploaded_file)[0]
        invalid_df = process_val(df, 'Action', uploaded_file)[1]
        st.write(valid_df)
        st.write(invalid_df)
    else:
        home(upload_file)

def general(uploaded_file):
    if uploaded_file:
        st.header('Plot of Data')
    else:
        home(upload_file)

# Add a title and intro text
st.title('SABC ML App')
st.text('Validation de la sémantique des diagnostics et actions menées sur GLPI')

# Sidebar setup
st.sidebar.title('FORMULAIRE')
upload_file = st.sidebar.file_uploader('Selectioner votre fichier ici')
#Sidebar navigation
st.sidebar.title('NAVIGATION')
options = st.sidebar.radio('Que voulez vous visualiser:', ['Accueil', 'Diagnostics', 'Actions menées', 'General'])


# Navigation options
if options == 'Accueil':
    home(upload_file)
elif options == 'Diagnostics':
    diagnostics(upload_file)
elif options == 'Actions menées':
    actions_menees(upload_file)
elif options == 'General':
    general(upload_file)