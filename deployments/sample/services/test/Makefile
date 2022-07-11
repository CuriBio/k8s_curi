ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/test
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t test . -f ${repo_root}/deployments/sample/services/test/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t test . --platform linux/amd64 --load

tag:
	docker tag test:latest $(ecr_repo):latest

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):latest

apply:
	kubectl apply -f ./manifests/

