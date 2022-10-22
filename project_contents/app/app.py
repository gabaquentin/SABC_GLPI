# Importer les librairies requises
import os
from io import BytesIO

import spacy

import streamlit as st


import pandas as pd
from PIL import Image

from st_aggrid import AgGrid

import plotly.graph_objects as go

from datarobot_predict import main

# Initialiser les variables globales
nlp = spacy.load("fr_core_news_sm")

st.set_page_config(layout="wide")

path = os.path.dirname(os.path.realpath('__file__'))

image_file = path+'/project_contents/app/logo.png'

if os.path.isfile(image_file):
    image = Image.open(image_file)
else:
    image = Image.open(path + '/logo.png')

st.session_state['FILE'] = bytearray()
st.session_state['DEPLOYMENT_ID'] = "633c3f5b9ee9f96d89b4df5b"

st.session_state['FILTRE'] = ['Secteurs',
                              'Région',
                              'Attribué à - Technicien',
                              'Etablissement',
                              'Service',
                              'Catégorie',
                              'Diagnostic Intervenant - Description',
                              'Qlté Diagnostic',
                              'Action(s) menée(s) - Action(s) menée(s)',
                              'Qlté Actions Menées']


def get_data(data, type, column_name):
    """
    Cette fonction permet de nettoyer le tableau en entre afin de ne garder que les colones qui seront necessaires
    pour le traitement des donnees

    :param csv data : Les donnees initiales
    :param str type : Le type de colonne à analyser [Diagnostic / Action]
    :param str column_name : Le nom de la colonne à analyser sur le fichier uploader
    :return Dataframe : Nouvelle Dataframe possedant uniquement les colones necessaires pour les calculs
    """

    # Load dataframe
    columns = ["Catégorie", type]
    renamed_columns = ["Catégorie", column_name]
    df = data[columns]

    # Rename documents title

    columns_to_rename = {}

    for index, column in enumerate(columns):
        columns_to_rename[column] = renamed_columns[index]
    df = df.rename(columns=columns_to_rename)

    # Drop NaN Fields
    df = df.dropna(axis=0)

    return df


def get_cleaned_cat(df, column_name):
    """
    Cette fonction permet de nettoyer les differentes categories en retirant les caracteres inutiles

    :param Dataframe df : Dataframe initial
    :param str column_name : Le nom de la colonne à analyser sur le fichier uploader
    :return list : Liste de toutes les categories nettoyées
    """

    all_cat = []
    for cat in df.groupby('Catégorie')[column_name].apply(list).index:
        result_str = ""
        for i in range(0, len(cat)):
            if cat[i] == '>' or cat[i] == '_' or cat[i] == '.' or cat[i] == ' ':
                break
            else:
                result_str = result_str + cat[i]
        all_cat.append(result_str)

    return all_cat


def get_cat_data(column_name, type):
    """
    Cette fonction permet de predire les categories des diffenrents champs en fesant appel au main du fichier datarobot.py

    :param str column_name: Le nom de la colonne à analyser sur le fichier uploader
    :param str type: Le type de colonne à analyser [Diagnostic / Action]
    :return Dataframe : Un Dataframe posséndant les differentes colonnes de predictions des donnees
    """

    df = get_data(st.session_state.FILE, type, column_name)
    df_to_predict = pd.DataFrame({'Description': []})
    df_to_predict['Description'] = df[column_name]

    if st.session_state.CAT_CORR:

        all_cat = get_cleaned_cat(df, column_name)
        for cat in all_cat:
            df.loc[df['Catégorie'].str.contains(cat), 'clean_categorie'] = cat
        predicted_df = 1

        predicted_df = main(df_to_predict.to_csv(), st.session_state.DEPLOYMENT_ID)

        df['predicted_categorie'] = ""
        df['predicted_categorie (%)'] = ""

        if predicted_df == 1:
            st.warning("API DATAROBOT Inactif veuillez contacter l'administrateur")
            st.session_state['CAT_CORR'] = False

        i = 0
        for k, v in df.iterrows():
            if predicted_df == 1:
                df['predicted_categorie'][k] = df['clean_categorie'][k]
            else:

                predicted = next((x for x in predicted_df['data'][i]['predictionValues'] if
                                  x["label"] == predicted_df['data'][i]['prediction']), None)
                if predicted != None:
                    if predicted['value'] >= 0.7:
                        df['predicted_categorie'][k] = predicted_df['data'][i]['prediction']
                        df['predicted_categorie (%)'][k] = predicted['value']
                    else:
                        df['predicted_categorie'][k] = df['clean_categorie'][k]
                        df['predicted_categorie (%)'][k] = predicted['value']
                else:
                    st.warning("Un probleme est survenu, recheargez la page et si ca persiste, contactez l'administrateur")
                    break
                i += 1

    return df

def validate_sentence(s):
    """
    Cette fonction permet de traiter le texte pour analyser sa syntaxe grammaticale

    :param s : Le texte à analyser
    :return bool : Vrai ou faux
    """
    doc = nlp(s.lower())
    num_token = 0
    for token in doc:
        if token.pos_ not in ['PUNCT', 'SPACE']:
            num_token += 1

    if num_token > 3:
        DEP_Counts = doc.count_by(spacy.attrs.DEP)
        num_dependency = 0
        core_arguments = ['nsubj', 'nsubj:outer', 'nsubj:pass', 'obj', 'iobj', 'csubj', 'csubj:outer', 'csubj:pass',
                          'ccomp', 'xcomp']
        nominal_dependency = ['nmod', 'nmod:poss', 'nmod:tmod', 'appos', 'nummod', 'nummod:gov', 'acl', 'acl:relcl',
                              'amod']
        non_core_dependents = ['obl', 'obl:agent', 'obl:arg', 'obl:lmod', 'obl:tmod', 'vocative', 'expl', 'expl:impers',
                               'expl:pass', 'expl:pv', 'dislocated', 'advcl', 'advmod', 'advmod:emph', 'advmod:lmod',
                               'discourse']
        dependency = core_arguments + nominal_dependency + non_core_dependents
        for k, v in sorted(DEP_Counts.items()):
            if doc.vocab[k].text in dependency:
                num_dependency += 1

        if num_dependency >= st.session_state.TOLERANCE_GRAMMATICALE:
            return True
        else:
            return False
    else:
        return False

def process_val(df, column_name, QColumn_name2):
    """
    Cette fonction permet de proceder a la validation des donnees en comparant les differents resultats obtenus dans la classification et l'analyse grammaticale des donnees pour avoir les resultats finaux

    :param Dataframe df : Dataframe initial
    :param str column_name : Le nom de la colonne à analyser sur le fichier uploader
    :param str QColumn_name2 : Le nom de la colonne où seras stocké le résultat
    :return Dataframe : Le Dataframe analysé et pret a la publication des resultats
    """

    df['valid_predict'] = True
    df[QColumn_name2] = False
    if st.session_state.CAT_CORR:
        for index, row in df.iterrows():
            if row['clean_categorie'] == row['predicted_categorie']:
                df['valid_predict'][index] = True
            else:
                df['valid_predict'][index] = False

    df['valid_sentence'] = df[column_name].apply(validate_sentence)
    df.loc[(df['valid_sentence'] == True) & (df['valid_predict'] == True), QColumn_name2] = True
    return df


def last_process(file, type, column_name, QColumn_name, QColumn_name2):
    """
    Cette fonction permet de remplir la colonne approprié dans le fichiers d'entree par les resultats obtenus dans la fonction process_val()

    :param csv file : Le fichier uploader et possédant les colonnes nécessaires
    :param str type : Le type de colonne à analyser [Diagnostic / Action]
    :param str column_name : Le nom de la colonne à analyser sur le fichier uploader
    :param str QColumn_name : Le nom de la colonne où seront stocker les résultats finaux sur le fichier uploader
    :param str QColumn_name2 : Le nom de la colonne où sont stockés les résultats obtenus sur le dataframe nettoyé
    :return Dataframe : Le Dataframe final avec la colonne QColumn_name2 modifié
    """

    df = get_cat_data(type, column_name)
    final_df = process_val(df, type, QColumn_name2)

    file[QColumn_name] = False
    for index, row in final_df.iterrows():
        file.loc[final_df[type][index] == file[column_name], QColumn_name] = final_df[QColumn_name2][index]

    st.session_state.FILE = file
    return file

def draw_pie(file, option, filtre, type):
    """
    Cette fonction permet de dessiner les graphes circulaires pour les statistiques

    :param csv file: Le fichier traite et possedant les resultats finaux
    :param str option: L'option de tri choisi par l'utilisateur
    :param str filtre: L'element de filtre choisie par l'utilisateur dans dans une option precise
    :param str type: Le type a filtrer [Diagnostic / Action / ActionG / DiagnosticG]
    :return : La figure resultante
    """
    labels = ['OK', 'NON OK']
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

def best_ratio(file, option, type):

    """
    Cette fonction permet de calculer le ratio ( Champs sémantiquement correcte/Total des champs ) en %
    :param csv file: Le fichier uploader et possédant les resultats finaux
    :param str option: L'option de tri choisi par l'utilisateur
    :param str type: La colonne a analyser
    :return: la liste complete des ratios par options
    """
    list = {}
    for val in file[option].unique():
        list[val] = (len(file[(file[option] == val) & (file[type] == True)]) / len(file[file[option] == val])) * 100

    return list

def draw_bar(element):

    """
    Cette fonction permet de dessiner l'histogramme des resultats obtenus
    :param element: la liste complete des ratios par options calculé dans la fonction best_ratio()
    :return: la figure resultantes
    """
    datay = []
    datax = []
    for k, v in element.items():
        datay.append(v)
        datax.append(k)
    fig = go.Figure(
        data=[go.Bar(x=datax, y=datay)],
        layout={'xaxis':
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

def to_excel(df):

    """
    Cette fonction permet de convertir un Dataframe en excel
    :param Dataframe df: Le dataframe a convertir
    :return : le fichier excel
    """
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

# Fonctions de navigation

def home():
    if len(st.session_state.FILE) > 0:
        st.header('Verifiez qu\'il s\'agissent bien du bon fichier')
        st.text(
            'Une fois le fichier verifié, vous cliquez sur une option dans le menu de navigation a ⬅️ gauche pour obtenir les 📊 resultats obtenus.')
        # st.write(df)
        AgGrid(st.session_state.FILE)
    else:
        st.header('Téléverser un fichier pour commencer')


def diagnostics():
    #Verifier si le fichier existe

    if len(st.session_state.FILE) > 0:
        #Afficher le titre

        st.header('DIAGNOSTICS')

        #Analyser le fichier d'entre

        file = last_process(file=st.session_state.FILE,
                            type='Diagnostic',
                            column_name='Diagnostic Intervenant - Description',
                            QColumn_name='Qlté Diagnostic',
                            QColumn_name2='QDiagnostic')

        #Afficher la liste des options disponibles

        option = st.selectbox(
            'Filtrer par',
            st.session_state.FILTRE)

        #Filtrer les options dans une liste

        filtre = st.selectbox(
            'Selectioner un élément',
            file[option].unique())

        #Afficher les differents graphes

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
            st.header("Tous les Éléments")
            st.plotly_chart(fig3, use_container_width=True)

        #Afficher le tableau des resultats obtenus en fonction du filtre choisie dans une option

        AgGrid(file[file[option] == filtre])
        #st.write(file[file[option] == filtre])

        #Convertir le dataframe en excel

        df_xlsx = to_excel(file[file[option] == filtre].drop('Qlté Actions Menées', axis=1))

        #Boutton de telechargement du fichier en excel en fonction du filtre choisi dans une option

        st.download_button(label='📥 Telecharger le fichier',
                           data=df_xlsx,
                           file_name='%s_qlte_diagnostic.xlsx' % os.path.splitext(st.session_state.FILE_NAME)[0])
    else:
        #Afficher la page d'accueil si le fichier existe pas

        home()


def actions_menees():
    #Verifier si le fichier existe

    if len(st.session_state.FILE) > 0:
        #Afficher le titre

        st.header('ACTIONS MENÉES')

        #Analyser le fichier d'entre

        file = last_process(file=st.session_state.FILE,
                            type='Action',
                            column_name='Action(s) menée(s) - Action(s) menée(s)',
                            QColumn_name='Qlté Actions Menées',
                            QColumn_name2='QAction')

        #Afficher la liste des options disponibles

        option = st.selectbox(
            'Filtrer par',
            st.session_state.FILTRE)

        #Filtrer les options dans une liste

        filtre = st.selectbox(
            'Selectioner un élément',
            file[option].unique())

        #Afficher les differents graphes

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
            st.header("Tous les Éléments")
            st.plotly_chart(fig3, use_container_width=True)

        #Afficher le tableau des resultats obtenus en fonction du filtre choisie dans une option

        AgGrid(file[file[option] == filtre])

        #Convertir le dataframe en excel

        df_xlsx = to_excel(file[file[option] == filtre].drop('Qlté Diagnostic', axis=1))

        #Boutton de telechargement du fichier en excel en fonction du filtre choisi dans une option

        st.download_button(label='📥 Telecharger le fichier',
                           data=df_xlsx,
                           file_name='%s_qlte_action_menee.xlsx' % os.path.splitext(st.session_state.FILE_NAME)[0])
    else:
        #Afficher la page d'accueil si le fichier existe pas

        home()


def general():
    #Verifier si le fichier existe

    if len(st.session_state.FILE) > 0:

        #Analyser le fichier d'entre

        file = last_process(file=st.session_state.FILE,
                            type='Diagnostic',
                            column_name='Diagnostic Intervenant - Description',
                            QColumn_name='Qlté Diagnostic',
                            QColumn_name2='QDiagnostic')
        file = last_process(file=file,
                            type='Action',
                            column_name='Action(s) menée(s) - Action(s) menée(s)',
                            QColumn_name='Qlté Actions Menées',
                            QColumn_name2='QAction')

        #Afficher le tableau des resultats obtenus au complet

        AgGrid(file)

        #Convertir le dataframe en excel

        df_xlsx = to_excel(file)

        #Boutton de telechargement du fichier complet en excel
        st.download_button(label='📥 Telecharger le fichier',
                           data=df_xlsx,
                           file_name='%s_qlte_champs.xlsx' % os.path.splitext(st.session_state.FILE_NAME)[0])

        #Afficher la liste des options disponibles

        option = st.selectbox(
            'Filtrer par',
            st.session_state.FILTRE)

        #Afficher les differents graphes

        # PIE
        piefig1 = draw_pie(file, option, "", "ActionG")
        piefig3 = draw_pie(file, option, "", "DiagnosticG")

        #BAR
        barfig1 = draw_bar(best_ratio(file, option, 'Qlté Actions Menées'))
        barfig3 = draw_bar(best_ratio(file, option, 'Qlté Diagnostic'))

        col1, col3 = st.columns(2)

        with col1:
            st.header("ACTIONS MENNEES")
            st.plotly_chart(barfig1, use_container_width=True)
            st.plotly_chart(piefig1, use_container_width=True)

        with col3:
            st.header("DIAGNOSTICS")
            st.plotly_chart(barfig3, use_container_width=True)
            st.plotly_chart(piefig3, use_container_width=True)

    else:
        #Afficher la page d'accueil si le fichier existe pas

        home()


#Afficher le titre de la page d'accueil

st.title('SABC ML App')
st.text('Validation de la sémantique des diagnostics et actions menées sur GLPI')

#Afficher le logo sur la barre laterale

with st.sidebar.container():
    logo = st.image(image)

#Afficher le formulaire sur la barre laterale

st.sidebar.title('FORMULAIRE')
upload_file = st.sidebar.file_uploader('Selectioner votre fichier ici')


#Afficher les options de navigation sur la barre laterale

st.sidebar.title('NAVIGATION')
options = st.sidebar.radio('Que voulez vous visualiser:', ['Accueil', 'Diagnostics', 'Actions menées', 'General'])

#Afficher les parametres sur la barre laterale
def sidebar_param(disabled=False):
    with st.sidebar:
        # Sidebar filter options
        st.sidebar.title('PARAMETRES')
        if 'TOLERANCE_GRAMMATICALE' in st.session_state and 'CAT_CORR' in st.session_state:
            TG = st.session_state.TOLERANCE_GRAMMATICALE
            CC = st.session_state.CAT_CORR
        else:
            TG = 1
            CC = False
        st.session_state.TOLERANCE_GRAMMATICALE = st.sidebar.slider('Tolerance grammatical', 0, 5, TG,
                                                                    disabled=disabled)
        st.session_state.CAT_CORR = st.checkbox('Correspondance a la categorie', CC, disabled=disabled)

#Verifier si le fichier uploade est correct

if upload_file is not None:

    #Enregistrer le nom et l'extension du fichier uploade

    st.session_state['FILE_NAME'], st.session_state['FILE_EXT'] = os.path.splitext(upload_file.name)

    #Verifier si l'extention du fichier uploader est valide

    if st.session_state['FILE_EXT'] in ['.xlsx', '.csv']:
        if st.session_state['FILE_EXT'] == '.xlsx':
            # Convertir le fichier excel en Dataframe
            uploaded_file = pd.DataFrame(pd.read_excel(upload_file, engine='openpyxl', header=1))
        else:
            # Convertir le fichier csv en Dataframe
            uploaded_file = pd.read_csv(upload_file, sep=';', error_bad_lines=False)
    else:
        #Si le fichier n'est pas valide, on sauvegarde un fichier vide et on affiche un message a l'ecran

        uploaded_file = bytearray()
        st.warning('Le fichier selectionner n\'est pas accepté. Les fichiers acceptés sont les suivants : \n '
                   '- .xlsx (Excel)\n '
                   '- .csv ')

    #Si un fichier est accepte, on vas verifier les diferentes colonnes qu'il possede
    if len(uploaded_file) > 0:
        all_column_in = True
        for k, v in pd.Series(st.session_state.FILTRE).isin(uploaded_file.columns).iteritems():
            if v == False:
                all_column_in = False
                break

        if all_column_in:
            #Si toutes les colonnes necessaires sont reperees, on enregistre notre fichier dans un variable globale

            st.session_state.FILE = uploaded_file
            st.session_state.FILE_NAME = upload_file.name

            # st.success('Fichier %s valide' % st.session_state.FILE_NAME)
        else:
            #Si toutes les colonnes necessaires ne sont pas reperees, on affiche un message d'erreur

            st.warning('Verifiez que votre fichier posséde au moins les colones : \n '
                       '- Secteurs \n '
                       '- Région \n '
                       '- Attribué à '
                       '- Technicien \n '
                       '- Etablissement \n '
                       '- Service \n '
                       '- Catégorie \n '
                       '- Diagnostic Intervenant - Description \n '
                       '- Qlté Diagnostic \n '
                       '- Action(s) menée(s) - Action(s) menée(s) \n '
                       '- Qlté Actions Menées \n '
                       'Indispensables pour notre application')

    if options == 'Accueil':
        #On affiche les parametres si nous sommes dans la page d'accueil uniquement

        sidebar_param()
else:
    #On desactive les parametres si nous ne sommes pas dans la page d'accueil

    sidebar_param(True)

#Options de navigation

if options == 'Accueil':
    home()
elif options == 'Diagnostics':
    diagnostics()
elif options == 'Actions menées':
    actions_menees()
elif options == 'General':
    general()
# %%
