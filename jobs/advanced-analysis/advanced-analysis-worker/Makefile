ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/advanced-analysis-worker
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t advanced-analysis-worker . -f ${repo_root}/jobs/advanced-analysis/advanced-analysis-worker/Dockerfile \
		--secret=id=CODE_ARTIFACT_ACCOUNT_ID \
		--secret=id=CODE_ARTIFACT_ACCESS_KEY \
		--secret=id=CODE_ARTIFACT_ACCESS_KEY_ID

buildx:
	cd ${repo_root} && \
	docker buildx build -t advanced-analysis-worker . -f ${repo_root}/jobs/advanced-analysis/advanced-analysis-worker/Dockerfile --platform linux/amd64 --load \
		--secret=id=CODE_ARTIFACT_ACCOUNT_ID \
		--secret=id=CODE_ARTIFACT_ACCESS_KEY \
		--secret=id=CODE_ARTIFACT_ACCESS_KEY_ID

tag:
	docker tag advanced-analysis-worker:latest $(ecr_repo):0.1.0rc9

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):0.1.0rc9

apply:
	kubectl apply -f ./manifests/
