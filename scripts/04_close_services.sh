#!/bin/bash
# aloittely, ei taida toimia.
# set -e -> pysähtyy virheeseen
set -e

# Poistetaan palvelut Azuren pilvestä
echo "Closing services"
cd infra/tf/services
terraform destroy -auto-approve
cd ../../..

# Poista Container Registry Azuresta
echo "Closing and deleting container registry"
cd infra/tf/container_registry
terraform destroy -auto-approve

echo "All resource groups deleted"