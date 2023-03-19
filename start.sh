# start docker
sudo service docker restart

# login to ECR from EC2
ecr_login=$(aws ecr get-login --region us-east-1 --no-include-email)
$ecr_login

# pull latest image
docker pull 729846226715.dkr.ecr.us-east-1.amazonaws.com/hesaving:latest

# run the app
docker run -d --rm -p 8000:8000 729846226715.dkr.ecr.us-east-1.amazonaws.com/hesaving