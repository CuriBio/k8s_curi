ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/pulse3d_api

repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t pulse3d_api . -f ${repo_root}/deployments/pulse3d/services/pulse3d/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t pulse3d_api . --platform linux/amd64 --load -f ${repo_root}/deployments/pulse3d/services/pulse3d/Dockerfile

tag:
	docker tag pulse3d_api:latest $(ecr_repo):0.3.0

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):0.3.0

apply:
	kubectl apply -f ./manifests/

