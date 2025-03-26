Flower prediction model that can be trained with new data continuously. Uses terraform to load 3 containers into Azure. Simple UI that can be used to load picture and to predict the correct flower category with .keras model. If predicted incorrectly, new model can be trained with same picture. New model will be used in next prediction.

<!---
# Kasvimallin käyttöönotto, sekä alasajo Azuressa.

## Tapa 1

### Aja ```run_all.sh``` scripti.

- Joudut kirjautumaan manuaalisesti Azureen sisään, sekä valitsemaan Subscriptionin.

### Aja ```04_close_services.sh``` scripti sammuttaaksesi palvelun.

## Tapa 2 - manuaalinen

### Ylösajo
- Kirjaudu azureen sisään komennolla ```az login```
- mene kansioon infra/tf/container_registry ja aja komennot ```terraform init``` sekä ```terraform apply```
- mene takaisin projektin root kansioon ja aja ```./scripts/01_acr_login.sh```
- Rakenna docker imaget ajamalla komennot (muista muuttaa numerot mikäli versio vaihtuu, tarkista tiedostosta ./infra/tf/services/variables.tf):
  - ```./scripts/02_build_n_release.sh flowerui 1.0```
  - ```./scripts/02_build_n_release.sh modeller 1.0```
  - ```./scripts/02_build_n_release.sh predictflower 1.0```

- Rakenna servicet, menemällä kansioon infra/tf/services ja ajamalla komennot: ```terraform init``` ja ```terraform apply```

### Alasajo.

- mene kansioon infra/tf/services ja aja komento: ```terraform destroy```
- mene kansioon infra/tf/container_registry ja aja komento: ```terraform destroy```
--->
#

# Deploying and Shutting Down the Plant Model in Azure
## Method 1 - Automated with 2 Scripts
### Run the ``run_all.sh`` script.
- You will need to log in to Azure manually and select the Subscription.

### Run the ``04_close_services.sh`` script to shut down the service.

## Method 2 - Manual
### Deployment
- Log in to Azure using the command: ``az login``
- Navigate to the infra/tf/container_registry directory and run the following commands:
``terraform init`` and ``terraform apply``
- Return to the project's root directory and run:
``./scripts/01_acr_login.sh``
- Build the Docker images by running the following commands (remember to change the version numbers if they change, check from file ./infra/tf/services/variables.tf):
  - ``./scripts/02_build_n_release.sh flowerui 1.0``
  - ``./scripts/02_build_n_release.sh modeller 1.0``
  - ``./scripts/02_build_n_release.sh predictflower 1.0``
- Deploy the services by navigating to the infra/tf/services directory and running:
``terraform init`` and ``terraform apply``

### Shutdown
- Navigate to the infra/tf/services directory and run:
``terraform destroy``
- Navigate to the infra/tf/container_registry directory and run:
``terraform destroy``
