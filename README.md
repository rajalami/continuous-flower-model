# Kasvimallin käyttöönotto, sekä alasajo Azuressa.

## Tapa 1

### Aja ```run_all.sh``` scripti.

- Joudut kirjautumaan manuaalisesti sisään, sekä valitsemaan Subscriptionin.

### Aja ```04_close_services.sh``` scripti sammuttaaksesi palvelun.

## Tapa 2 - manuaalinen

### Ylösajo
- Kirjaudu azureen sisään komennolla ```az login```
- mene kansioon infra/tf/container_registry ja aja komennot ```terraform init``` sekä ```terraform apply```
- mene takaisin projektin root kansioon ja aja ```./scripts/01_acr_login.sh```
- Rakenna docker imaget ajamalla komennot (muista muuttaa numerot mikäli versio vaihtuu):
  - ```./scripts/02_build_n_release.sh flowerui 1.0```
  - ```./scripts/02_build_n_release.sh modeller 1.0```
  - ```./scripts/02_build_n_release.sh predictflower 1.0```

- Rakenna servicet, menemällä kansioon infra/tf/services ja ajamalla komennot: ```terraform init``` ja ```terraform apply```

### Alasajo.

- mene kansioon infra/tf/services ja aja komento: ```terraform destroy```
- mene kansioon infra/tf/container_registry ja aja komento: ```terraform destroy```
  

