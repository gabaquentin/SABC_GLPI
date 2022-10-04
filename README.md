# SABC GLPI MACHINE LEARNING NLP

###### Tout au long de ce projet, nous avons combiner plusieurs techniques du machine learning afin de mettre sur pied une solution capable d'analyser des textes extraites de GLPI pour analyser leurs structures.
###### Avant de passer au vif du sujet, nous allons d'abord installer les differents modules et packages necessaires au bon fonctionnement de notre application.

## MODULES ET PACKAGES NECESSAIRES

`Python 3.6`

`pip install : `

>- streamlit == 1.10.0
>
> Permet de creer des applications en python pure, et aucune connaissance en frontend n'est requis. 

>- spacy == 2.3.5
>Il s'agit ici d'une bibliothèque avancée pour le traitement du langage naturel en python et Cython.
> 

>- pandas == 1.1.5
>
> pandas est un package Python qui fournit des structures de données rapides, flexibles et expressives conçues pour rendre le travail avec des données "relationnelles" ou "étiquetées" facile et intuitive.

>- datarobot == 2.28.1
>
> Bibliotheque cliente pour travailler avec l'API de la plateforme [Datarobot]('http://datarobot.com/)

>- streamlit-aggrid = 0.2.2.post2
>
> Utilise ici pour afficher nos dataframe avec plusieurs possibilités de filtres. 

>- plotly == 5.6.0
>
> Bibliothèque graphique interactive avec laquelle l'on a dessiné nos different graphes 

>- xlsxwriter == 3.0.3
>
> Module python permettant d'enregistrer le fichier final sous excel

###### Une fois les modules et packages installes, nous pouvons proceder au lancement du projet 

## LANCER LE PROJET EN LOCAL
`1- Ouvrez un terminal dans le dossier /app `

`2- lancez la commande suivante :  `
>streamlit run app.py --server.maxUploadSize 20000

## LANCER LE PROJET DANS LE CLOUD 'AZURE'

### Le necessaire

###### Installer le Docker engine en fonction de la plateforme utilisé (Windows/Mac os/Ubuntu)
###### Installer le client azure
###### Assurez vous d'avoir un compte azure avec un abonnement actif pour pouvoir deployer le projet

### Deployer le projet sur azure

###### Lancer les commandes suivantes dans l'ordre 
> `docker build -t sabc_glpi:v1 . `
> 
> `docker tag sabc_glpi:v1 sabcglpireg.azurecr.io/sabc_glpi:v1`
>
> `az acr login -n sabcglpireg`
>
> `docker push sabcglpireg.azurecr.io/sabc_glpi:v1`
> 
> `az container create --resource-group SABC_GLPI_GROUP --name valsem -f deployment.yml`

### Ouvrir le projet en cliquant via ce lien 
>http://castelafrique.francecentral.azurecontainer.io
###### Ou en vous rendant dans votre projet sur le site d'azure