# TODO ADD YOUR ECR REPO URL
ecr_repo = ???

.PHONY: build buildx push tag apply
build:
	docker build -t ${service_name} .

buildx:
	docker buildx build -t ${service_name} . --platform linux/amd64 --load

tag:
	docker tag ${service_name}:latest $(ecr_repo):latest

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):latest

apply:
	kubectl apply -f ./manifests/

