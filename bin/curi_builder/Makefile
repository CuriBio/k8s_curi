# TODO ADD YOUR ECR REPO URL
ecr_repo = 245339368379.dkr.ecr.us-east-2.amazonaws.com/builder

.PHONY: build buildx push tag apply
build:
	docker build -t builder . 

buildx:
	docker buildx build -t builder . --platform linux/amd64 --load

tag:
	docker tag builder:latest $(ecr_repo):latest

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):latest

apply:
	kubectl apply -f ./manifests/

