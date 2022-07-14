ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/test2
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t test2 . -f ${repo_root}/deployments/sample/services/test2/Dockerfile

buildx:
	docker buildx build -t test2 . --platform linux/amd64 --load

tag:
	docker tag test2:latest $(ecr_repo):latest

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):latest

apply:
	kubectl apply -f ./manifests/

