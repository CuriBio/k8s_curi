ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/pulse3d-worker
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t pulse3d-worker . -f ${repo_root}/jobs/pulse3d/pulse3d-worker/Dockerfile \
		--secret=id=CODE_ARTIFACT_ACCOUNT_ID \
		--secret=id=CODE_ARTIFACT_ACCESS_KEY \
		--secret=id=CODE_ARTIFACT_ACCESS_KEY_ID

buildx:
	cd ${repo_root} && \
	docker buildx build -t pulse3d-worker . -f ${repo_root}/jobs/pulse3d/pulse3d-worker/Dockerfile --platform linux/amd64 --load \
		--secret=id=CODE_ARTIFACT_ACCOUNT_ID \
		--secret=id=CODE_ARTIFACT_ACCESS_KEY \
		--secret=id=CODE_ARTIFACT_ACCESS_KEY_ID

tag:
	docker tag pulse3d-worker:latest $(ecr_repo):2.0.0

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):2.0.0

apply:
	kubectl apply -f ./manifests/
