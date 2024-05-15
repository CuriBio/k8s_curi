ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/event-broker
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t event-broker . -f ${repo_root}/deployments/apiv2/services/event-broker/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t event-broker . -f ${repo_root}/deployments/apiv2/services/event-broker/Dockerfile --platform linux/amd64 --load

tag:
	docker tag event-broker:latest $(ecr_repo):0.1.0

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):0.1.0
