# SABC_GLPI
Validation de la sémantiques des données des champs ( Diagnostics et actions menées ) sous GLPI

## Command build and deploy to azure
docker build -t sabc_glpi:v1 .
docker tag sabc_glpi:v1 sabcglpireg.azurecr.io/sabc_glpi:v1

az acr login -n sabcglpireg

docker push sabcglpireg.azurecr.io/sabc_glpi:v1

### DEPLOY
az container create --resource-group SABC_GLPI_GROUP --name valsem -f deployment.yml