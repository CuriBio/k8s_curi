ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/mantarray
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t mantarray . -f ${repo_root}/deployments/apiv2/services/mantarray/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t mantarray . --platform linux/amd64 --load -f ${repo_root}/deployments/apiv2/services/mantarray/Dockerfile

tag:
	docker tag mantarray:latest $(ecr_repo):0.6.4

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):0.6.4