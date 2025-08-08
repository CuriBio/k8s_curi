ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/advanced-analysis-api
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t advanced-analysis-api . -f ${repo_root}/deployments/apiv2/services/advanced-analysis-api/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t advanced-analysis-api . -f ${repo_root}/deployments/apiv2/services/advanced-analysis-api/Dockerfile --platform linux/amd64 --load

tag:
	docker tag advanced-analysis-api:latest $(ecr_repo):0.2.3

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):0.2.3
