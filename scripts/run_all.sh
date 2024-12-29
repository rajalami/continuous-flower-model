#!/bin/bash

# Run this from the root of the project. Auto approves everything.

# set -e = quits if error
set -e

echo "Loggint into azure."
az login # must pick profile and subscription manually.

# Create Azure container registry
echo "Create container registry"
cd infra/tf/container_registry
terraform init --upgrade
terraform apply -auto-approve
cd ../../../ # back to root

# Login into azure container registry
echo "Login into azure container registry"
./scripts/01_acr_login.sh

# Build Docker-images
echo "Build docker images"
./scripts/02_build_n_release.sh flowerui 1.0
./scripts/02_build_n_release.sh modeller 1.0
./scripts/02_build_n_release.sh predictflower 1.0

# Start services
echo "Starting services"
cd infra/tf/services
terraform init --upgrade
terraform apply -auto-approve
