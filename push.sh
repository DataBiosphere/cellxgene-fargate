#!/bin/bash

# Perform docker login
$(aws ecr get-login --region=us-east-1 | python3 -c 'print(input().replace("-e none", ""))')

docker build --tag=$1 .
docker tag $1 122796619775.dkr.ecr.us-east-1.amazonaws.com/$1
docker push 122796619775.dkr.ecr.us-east-1.amazonaws.com/$1


