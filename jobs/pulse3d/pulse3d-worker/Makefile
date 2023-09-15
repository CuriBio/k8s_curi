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
<<<<<<< HEAD
	docker tag pulse3d-worker:latest $(ecr_repo):0.34.1
=======
	docker tag pulse3d-worker:latest $(ecr_repo):0.34.2
>>>>>>> RC-09-14-23

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
<<<<<<< HEAD
	docker push $(ecr_repo):0.34.1
=======
	docker push $(ecr_repo):0.34.2
>>>>>>> RC-09-14-23

apply:
	kubectl apply -f ./manifests/

