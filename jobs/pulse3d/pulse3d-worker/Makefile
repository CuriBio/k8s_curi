ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/pulse3d-worker
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t pulse3d-worker . -f ${repo_root}/jobs/pulse3d/pulse3d-worker/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t pulse3d-worker . -f ${repo_root}/jobs/pulse3d/pulse3d-worker/Dockerfile --platform linux/amd64 --load

tag:
	docker tag pulse3d-worker:latest $(ecr_repo):0.26.1

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):0.26.1

apply:
	kubectl apply -f ./manifests/

