#Import the required Libraries

import threading
import time
from os.path import exists

import spacy
import streamlit as st
import pandas as pd

import subprocess

from st_aggrid import AgGrid
from text_hammer.utils import nlp

st.set_page_config(layout="wide")

#GLOBAL VAR

st.session_state['TOLERANCE_GRAMMATICALE'] =0
st.session_state['CAT_CORR'] =False

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
        df_to_predict = pd.DataFrame({'Titre' : []})
        df_to_predict['Titre'] = df[fo_r]

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
    Qrow = ''
    if fo_r == 'Diagnostic':
        data_path = './data/diagnostic'
        Qrow = 'QDiagnostic'
    elif fo_r == 'Action':
        data_path = './data/action'
        Qrow = 'QAction'

    final_df = exists('{}/final_{}'.format(data_path, uploaded_file.name))

    if final_df:
        return pd.read_csv("{}/final_{}".format(data_path, uploaded_file.name))
    else:
        df['valid_predict'] = True
        if st.session_state.CAT_CORR :
            df[df['clean_categorie'] == df['predicted_categorie'], 'valid_predict'] = True
            df[df['clean_categorie'] != df['predicted_categorie'], 'valid_predict'] = False

        df['valid_sentence'] = df[fo_r].apply(validateSentence)

        df.loc[(df['valid_sentence'] == True) & (df['valid_predict'] == True), Qrow] = True
        df.loc[(df['valid_sentence'] == False) | (df['valid_predict'] == False), Qrow] = False

        df.to_csv("{}/final_{}".format(data_path, uploaded_file.name), index=False)

        return df

# sentences validations functions
def validateSentences(s):
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

def validateSentence(s):
    doc = nlp(s.lower())
    DEP_Counts = doc.count_by(spacy.attrs.DEP)
    num_dependency = 0
    core_arguments = ['nsubj', 'obj', 'iobj', 'csubj', 'ccomp', 'xcomp']
    nominal_dependency = ['nmod', 'appos', 'numod', 'acl', 'amod', 'det', 'clf', 'case']
    non_core_dependents = ['obl', 'vocative', 'expl', 'dislocated', 'advcl', 'advmod', 'discourse', 'aux', 'cop', 'mark']
    for k,v in sorted(DEP_Counts.items()) :
        if doc.vocab[k].text in core_arguments or doc.vocab[k].text in nominal_dependency or doc.vocab[k].text in non_core_dependents:
            num_dependency+=1
    if num_dependency < st.session_state.TOLERANCE_GRAMMATICALE:
        return False

    return True
# Functions for each of the pages
def home(uploaded_file):
    if uploaded_file:
        st.header('Verifiez qu\'il s\'agissent bien du bon fichier')
        st.text('Une fois le fichier verifié, vous cliquez sur une option dans le menu de navigation a ⬅️ gauche pour obtenir un 📊 recapitulatif de la validation de la semantique des données des saisient')
        df = pd.read_csv(upload_file, sep=';')
        AgGrid(df)
    else:
        st.header('Téléverser un fichier pour commencer')

def diagnostics(uploaded_file):
    if uploaded_file:
        st.header('DIAGNOSTICS')
        df = get_cat_data(uploaded_file, 'Diagnostic', 'Diagnostic Intervenant - Description')
        final_df = process_val(df, 'Diagnostic', uploaded_file)
        valid_df = final_df[final_df['QDiagnostic'] == True]
        invalid_df = final_df[final_df['QDiagnostic'] == False]
        st.write(len(df))
        st.write(len(valid_df))
        st.write(len(invalid_df))

        AgGrid(df)
        #st.write(df)

        st.text('DIAGNOSTICS CORRECTES')
        AgGrid(valid_df)
        #st.write(valid_df)

        st.text('DIAGNOSTICS INCORRECTES')
        AgGrid(invalid_df)
        #st.write(invalid_df)
    else:
        home(upload_file)

def actions_menees(uploaded_file):
    if uploaded_file:
        st.header('ACTIONS MENÉES')
        df = get_cat_data(uploaded_file, 'Action', 'Action(s) menée(s) - Action(s) menée(s)')
        final_df = process_val(df, 'Action', uploaded_file)
        valid_df = final_df[final_df['QAction'] == True]
        invalid_df = final_df[final_df['QAction'] == False]
        st.write(len(df))
        st.write(len(valid_df))
        st.write(len(invalid_df))

        AgGrid(df)
        #st.write(df)

        st.text('DIAGNOSTICS CORRECTES')
        AgGrid(valid_df)
        #st.write(valid_df)

        st.text('DIAGNOSTICS INCORRECTES')
        AgGrid(invalid_df)
        #st.write(invalid_df)
    else:
        home(upload_file)

def general(uploaded_file):
    if uploaded_file:
        st.header('Dashbord')
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

#st.write("I'm ", age, 'years old')

def sidebar_param(disabled = False):
    with st.sidebar:
        #Sidebar filter options
        st.sidebar.title('PARAMETRES')
        st.session_state.TOLERANCE_GRAMMATICALE = st.sidebar.slider('Tolerance grammatical', 0, 5, 1, disabled=disabled)
        st.session_state.CAT_CORR = st.checkbox('Correspondance a la categorie', disabled=disabled)

if upload_file is not None and options == 'Accueil':
    sidebar_param()
else:
    sidebar_param(True)

# Navigation options
if options == 'Accueil':
    home(upload_file)
elif options == 'Diagnostics':
    diagnostics(upload_file)
elif options == 'Actions menées':
    actions_menees(upload_file)
elif options == 'General':
    general(upload_file)