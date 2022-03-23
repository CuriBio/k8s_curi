# TODO ADD YOUR ECR REPO URL
ecr_repo = ???
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t pulse3d . -f ${repo_root}/deployments/pulse3d/services/pulse3d/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t pulse3d . --platform linux/amd64 --load -f ${repo_root}/deployments/pulse3d/services/pulse3d/Dockerfile

tag:
	docker tag pulse3d:latest $(ecr_repo):latest

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):latest

apply:
	kubectl apply -f ./manifests/

