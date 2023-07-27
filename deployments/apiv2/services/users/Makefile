ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/users
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t users . -f ${repo_root}/deployments/apiv2/services/users/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t users . -f ${repo_root}/deployments/apiv2/services/users/Dockerfile --platform linux/amd64 --load

tag:
	docker tag users:latest $(ecr_repo):0.6.3

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):0.6.3

apply:
	kubectl apply -f ./manifests/

