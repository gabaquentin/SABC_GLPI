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
>
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

>- xlrd == 2.0.1 et openpyxl == 3.0.10
>
> Modules python permettant de lire les fichiers excel

###### Une fois les modules et packages installes, nous pouvons proceder au lancement du projet 

## LANCER LE PROJET EN LOCAL
`1- Ouvrez un terminal dans le dossier ./project_contents/app `

`2- lancez la commande suivante :  `
>streamlit run app.py --server.maxUploadSize 20000
###### Le parametre `--server.maxUploadSize` permet de definir la taille maximale du fichier a uploader
###### Ici : `20000` pour `20 GB`
## LANCER LE PROJET DANS LE CLOUD 'AZURE'

### Le necessaire

###### Installer le Docker engine en fonction de la plateforme utilisé (Windows/Mac os/Ubuntu) ici : https://docs.docker.com/get-docker/
###### Installer le client azure ici : https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
***Assurez vous d'avoir un compte azure avec un abonnement actif pour pouvoir deployer le projet***

### Deployer le projet sur azure

###### Lancer les commandes suivantes dans l'ordre 
> ###### 1- Coordonner le deploiement dans Docker
> ###### Le fichier `Dockerfile` contient la configuration pour la dockerisation 
> ###### Le fichier `run.sh` contient la commande pour lancer notre application
> ###### Le fichier `environment.yml` contient la liste des paquets necessaires pour executer l'application
> Les commandes suivantes permettent de dockeriser l'application
>
> `docker build -t sabc_glpi:v1 . `
> 
> `docker tag sabc_glpi:v1 sabcglpireg.azurecr.io/sabc_glpi:v1`
>

> ###### 2- Deployer l'application dockeriser sur Azure
>- A executer une seule fois lors de la creation du registre de conteneur ici `sabcglpireg`
> ###### Dans le cas ou le registre est deja cree, aller a l'etape `Se connecter au registre` 
> ###### Lancer la commande suivante pour se connecter a azure
> `az acr login`
> ###### Ensuite, nous devons creer un groupe de ressource dans azure
> ###### Puis telecharger l'image du conteneur vers Azure Container Registry avec la commande suivante
> `az acr create --resource-group SABC_GLPI_GROUP --name sabcglpireg --sku Basic`
> 
>- A executera chaque fois que l'on veut pousser un nouveau conteneur vers le registre de conteneurs Azure a la place de l'ancien
>
> ###### Se connecter au registre
> `az acr login -n sabcglpireg`
> ###### Pousser le conteneur
> `docker push sabcglpireg.azurecr.io/sabc_glpi:v1`
> ###### Deployer l'application
> `az container create --resource-group SABC_GLPI_GROUP --name valsem -f deployment.yml`

### Ouvrir le projet en cliquant sur ce lien 
>http://castelafrique.francecentral.azurecontainer.io
###### Ou en vous rendant dans votre projet sur le site d'azure