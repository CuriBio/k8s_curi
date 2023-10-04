ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/jobs-operator

repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t jobs-operator . -f ${repo_root}/jobs/jobs-operator/jobs-operator/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t jobs-operator . --platform linux/amd64 --load -f ${repo_root}/jobs/jobs-operator/jobs-operator/Dockerfile

tag:
	docker tag jobs-operator:latest $(ecr_repo):0.0.3

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):0.0.3

apply:
	kubectl apply -f ./manifests/

