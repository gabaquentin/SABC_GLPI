#Import the required Libraries
import os
import threading
from io import BytesIO

import spacy
import streamlit as st
import pandas as pd
from PIL import Image

import subprocess
from st_aggrid import AgGrid

import plotly.graph_objects as go

from datarobot_predict import  main

nlp = spacy.load("fr_core_news_sm")

st.set_page_config(layout="wide")

path = os.path.dirname(os.path.realpath('__file__'))
#image_file = path+'/project_contents/app/logo.png'
image_file = path+'/logo.png'
image = Image.open(image_file)

#GLOBAL VAR

st.session_state['FILE'] = bytearray()
st.session_state['TEMP_FILE'] = bytearray()
st.session_state['FILE_NAME'] = ""
st.session_state['DEPLOYMENT_ID'] = "6329929cd452ce5ad78adfe7"

st.session_state['FILTRE'] = ['Secteurs', 'Région', 'Attribué à - Technicien','Etablissement','Service','Catégorie']

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

# Get all data function
def get_data(data, this, fo_r):
    #Load dataframe
    columns = ["Catégorie", this]
    renamed_columns = ["Catégorie", fo_r]
    df = data[columns]

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

#get dataframe categorized
def get_cat_data(fo_r, this):
    if len(st.session_state.TEMP_FILE) > 0:
        return st.session_state.TEMP_FILE

    else:
        #Premierement, on vas categoriser les diagnostics, car un bon diagnostic doit pouvoir appartenir a sa categorie d'origine
        df = get_data(st.session_state.FILE, this, fo_r)
        df_to_predict = pd.DataFrame({'Description' : []})
        df_to_predict['Description'] = df[fo_r]
        predicted_df = 1
        all_cat = get_cleaned_cat(df, fo_r)

        for cat in all_cat:
            df.loc[df['Catégorie'].str.contains(cat), 'clean_categorie'] = cat

        df['predicted_categorie'] = ""

        if st.session_state.CAT_CORR:
            predicted_df = main(df_to_predict.to_csv(), st.session_state.DEPLOYMENT_ID)

            if predicted_df == 1:
                st.warning("Un probleme est survenu, recheargez la page et si ca persiste, contactez l'administrateur")

            i = 0
            for k, v in df.iterrows():
                df['predicted_categorie'][k] = predicted_df['data'][i]['prediction']
                i+=1

        return df

#process validation function
def process_val(df, fo_r):
    Qrow = ''
    if fo_r == 'Diagnostic':
        Qrow = 'QDiagnostic'
    elif fo_r == 'Action':
        Qrow = 'QAction'

    if len(st.session_state.TEMP_FILE) > 0:
        return st.session_state.TEMP_FILE
    else:
        df['valid_predict'] = True
        if st.session_state.CAT_CORR :
            for index, row in df.iterrows():
                if row['clean_categorie'] == row['predicted_categorie']:
                    df['valid_predict'][index] = True
                else:
                    df['valid_predict'][index] = False

        df['valid_sentence'] = df[fo_r].apply(validateSentence)
        df.loc[(df['valid_sentence'] == True) & (df['valid_predict'] == True), Qrow] = True
        df.loc[(df['valid_sentence'] == False) | (df['valid_predict'] == False), Qrow] = False

        return df

def last_process(file, this, fo_r, r_fo_r, p_fo_r):
    df = get_cat_data(this, fo_r)

    final_df = process_val(df, this)
    i = 0
    for index, row in file.iterrows():
        if pd.isnull(row[fo_r]):
            file[r_fo_r][index] = False
        else:
            if i in final_df.index:
                file[r_fo_r][index] = final_df[p_fo_r][i]
            else:
                file[r_fo_r][index] = final_df[p_fo_r][index]
            i+=1
    st.session_state.FILE = file
    return file
# sentences validations functions

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

def draw_pie(file, option, filtre, type ):
    labels = ['OK','NON OK']
    if type == 'Diagnostic':
        values = [
            len(file[(file[option] == filtre) & (file['Qlté Diagnostic'] == True)]['Qlté Diagnostic']),
            len(file[(file[option] == filtre) & (file['Qlté Diagnostic'] == False)]['Qlté Diagnostic'])
        ]
    elif type == 'Action':
        values = [
            len(file[(file[option] == filtre) & (file['Qlté Actions Menées'] == True)]['Qlté Actions Menées']),
            len(file[(file[option] == filtre) & (file['Qlté Actions Menées'] == False)]['Qlté Actions Menées'])
        ]
    elif type == 'DiagnosticG':
        values = [
            len(file[file['Qlté Diagnostic'] == True]['Qlté Diagnostic']),
            len(file[file['Qlté Diagnostic'] == False]['Qlté Diagnostic'])
        ]
    elif type == 'ActionG':
        values = [
            len(file[file['Qlté Actions Menées'] == True]['Qlté Actions Menées']),
            len(file[file['Qlté Actions Menées'] == False]['Qlté Actions Menées'])
        ]
    else:
        values = [
            len(file[file['Qlté Actions Menées'] == True]['Qlté Actions Menées']),
            len(file[file['Qlté Actions Menées'] == False]['Qlté Actions Menées'])
        ]


    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3, pull=[0, 0.2])])

    return fig

def draw_bar(element):

    datay = []
    datax = []
    for k,v in element.items():
        datay.append(v)
        datax.append(k)
    fig = go.Figure(
        data=[go.Bar(x=datax, y=datay)],
        layout = {'xaxis':
                      {'title': 'Elements',
                            'visible': False,
                            'showticklabels': False
                       },
                    'yaxis':
                        {'title': 'Performances (%)',
                            'visible': True,
                            'showticklabels': True
                         }
                  }
    )
    return fig

def best_ratio(file, option, type):
    list = {}
    for val in file[option].unique():
        list[val] = (len(file[(file[option] == val) & (file[type] == True)])/len(file[file[option] == val]))*100

    return list
    # Functions for each of the pages

def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    format1 = workbook.add_format({'num_format': '0.00'})
    worksheet.set_column('A:A', None, format1)
    writer.save()
    processed_data = output.getvalue()
    return processed_data

def home():
    uploaded_file = st.session_state.FILE
    if len(uploaded_file) > 0:
        st.header('Verifiez qu\'il s\'agissent bien du bon fichier')
        st.text('Une fois le fichier verifié, vous cliquez sur une option dans le menu de navigation a ⬅️ gauche pour obtenir les 📊 resultats obtenus.')
        #st.write(df)
        AgGrid(uploaded_file)
    else:
        st.header('Téléverser un fichier pour commencer')

def diagnostics():
    if len(st.session_state.FILE) > 0:
        st.header('DIAGNOSTICS')
        file = last_process(file=st.session_state.FILE,this='Diagnostic', fo_r='Diagnostic Intervenant - Description', r_fo_r='Qlté Diagnostic', p_fo_r='QDiagnostic')

        option = st.selectbox(
            'Filtrer par',
            st.session_state.FILTRE)

        filtre = st.selectbox(
            'Selectioner une valeure',
            file[option].unique())

        fig1 = draw_pie(file, option, filtre, "Diagnostic")
        fig2 = draw_pie(file, option, filtre, "DiagnosticG")
        fig3 = draw_bar(best_ratio(file, option, 'Qlté Diagnostic'))

        col1, col2, col3 = st.columns(3)

        with col1:
            st.header("Par %s" % option)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.header("General")
            st.plotly_chart(fig2, use_container_width=True)

        with col3:
            st.header("Par ratio")
            st.plotly_chart(fig3, use_container_width=True)
        AgGrid(file[file[option] == filtre])
        df_xlsx = to_excel(file[file[option] == filtre].drop('Qlté Actions Menées', axis=1))
        st.download_button(label='📥 Telecharger le fichier',
                           data=df_xlsx ,
                           file_name= '%s_qlte_diagnostic.xlsx' % os.path.splitext(st.session_state.FILE_NAME)[0])
    else:
        home()

def actions_menees():
    if len(st.session_state.FILE) > 0:
        st.header('ACTIONS MENÉES')
        file = last_process(file=st.session_state.FILE,this='Action', fo_r='Action(s) menée(s) - Action(s) menée(s)', r_fo_r='Qlté Actions Menées', p_fo_r='QAction')

        option = st.selectbox(
            'Filtrer par',
            st.session_state.FILTRE)

        filtre = st.selectbox(
            'Selectioner une valeure',
            file[option].unique())

        fig1 = draw_pie(file, option, filtre, "Action")
        fig2 = draw_pie(file, option, filtre, "ActionG")
        fig3 = draw_bar(best_ratio(file, option, 'Qlté Actions Menées'))

        col1, col2, col3 = st.columns(3)

        with col1:
            st.header("Par %s" % option)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.header("General")
            st.plotly_chart(fig2, use_container_width=True)

        with col3:
            st.header("Ratio par %s" % option)
            st.plotly_chart(fig3, use_container_width=True)
        AgGrid(file[file[option] == filtre])
        df_xlsx = to_excel(file[file[option] == filtre].drop('Qlté Diagnostic', axis=1))
        st.download_button(label='📥 Telecharger le fichier',
                           data=df_xlsx ,
                           file_name= '%s_qlte_action_menee.xlsx' % os.path.splitext(st.session_state.FILE_NAME)[0])
    else:
        home()

def general():
    if len(st.session_state.FILE) > 0:
        file = last_process(file=st.session_state.FILE,this='Diagnostic', fo_r='Diagnostic Intervenant - Description', r_fo_r='Qlté Diagnostic', p_fo_r='QDiagnostic')
        file = last_process(file=file,this='Action', fo_r='Action(s) menée(s) - Action(s) menée(s)', r_fo_r='Qlté Actions Menées', p_fo_r='QAction')

        AgGrid(file)
        df_xlsx = to_excel(file)
        st.download_button(label='📥 Telecharger le fichier',
                           data=df_xlsx ,
                           file_name= '%s_qlte_champs.xlsx' % os.path.splitext(st.session_state.FILE_NAME)[0])
    else:
        home()

# Add a title and intro text
st.title('SABC ML App')
st.text('Validation de la sémantique des diagnostics et actions menées sur GLPI')

with st.sidebar.container():
    logo = st.image(image)
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
        if 'TOLERANCE_GRAMMATICALE' in st.session_state and 'CAT_CORR' in st.session_state:
            TG = st.session_state.TOLERANCE_GRAMMATICALE
            CC = st.session_state.CAT_CORR
        else:
            TG = 1
            CC = False
        st.session_state.TOLERANCE_GRAMMATICALE = st.sidebar.slider('Tolerance grammatical', 0, 5, TG, disabled=disabled)
        st.session_state.CAT_CORR = st.checkbox('Correspondance a la categorie', CC, disabled=disabled)

if upload_file is not None:

    uploaded_file = pd.read_csv(upload_file, sep=';')

    all_column_in = True
    for k,v in pd.Series(st.session_state.FILTRE).isin(uploaded_file.columns).iteritems():
        if v == False:
            all_column_in = False
            break
    if all_column_in:
        st.session_state.FILE = uploaded_file
        st.session_state.FILE_NAME = upload_file.name
        #st.success('Fichier %s valide' % st.session_state.FILE_NAME)
    else:
        st.warning('Verifiez que votre fichier posséde au moins les colones : \n '
                   '- Secteurs \n '
                   '- Région \n '
                   '- Attribué à '
                   '- Technicien \n '
                   '- Etablissement \n '
                   '- Service \n '
                   '- Catégorie \n '
                   'Indispensables pour notre application')

    if options == 'Accueil':
        sidebar_param()
else:
    sidebar_param(True)

# Navigation options
if options == 'Accueil':
    home()
elif options == 'Diagnostics':
    diagnostics()
elif options == 'Actions menées':
    actions_menees()
elif options == 'General':
    general()
#%%
