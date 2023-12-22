ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/queue-processor

repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t queue-processor . -f ${repo_root}/jobs/queue-processor/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t queue-processor . --platform linux/amd64 --load -f ${repo_root}/jobs/queue-processor/Dockerfile

tag:
	docker tag queue-processor:latest $(ecr_repo):0.0.8

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):0.0.8

apply:
	kubectl apply -f ./manifests/

