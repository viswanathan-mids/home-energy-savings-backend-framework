#!/bin/bash

# Build local docker image
docker build --platform=linux/amd64 -t hesaving .

# Login to AWS ECR
aws ecr get-login-password  --region us-east-1 | docker login --username AWS --password-stdin 729846226715.dkr.ecr.us-east-1.amazonaws.com

sleep 3

# Tag latest image
docker tag hesaving:latest 729846226715.dkr.ecr.us-east-1.amazonaws.com/hesaving

# Push to ECR
docker push 729846226715.dkr.ecr.us-east-1.amazonaws.com/hesaving

# Login to AWS EC2
ssh -i hesavingapi.pem ec2-user@ec2-44-214-125-207.compute-1.amazonaws.com 'bash -s' < ./start.sh

# Below start.sh script is in current dir
# start docker
# sudo service docker restart

# login to ECR from EC2
#ecr_login=$(aws ecr get-login --region us-east-1 --no-include-email)
#$ecr_login

# pull latest image
#docker pull 729846226715.dkr.ecr.us-east-1.amazonaws.com/hesaving:latest

# run the app
#docker run -d --rm -p 8000:8000 729846226715.dkr.ecr.us-east-1.amazonaws.com/hesaving