ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/uploader
repo_root=$(shell git rev-parse --show-toplevel)

.PHONY: build buildx push tag apply
build:
	cd ${repo_root} && \
	docker build -t uploader . -f ${repo_root}/frontend/pulse3d/Dockerfile

buildx:
	cd ${repo_root} && \
	docker buildx build -t uploader . -f ${repo_root}/frontend/pulse3d/Dockerfile --platform linux/amd64 --load --build-arg CLUSTER=test

# tag:
# 	docker tag users:latest $(ecr_repo):0.7.9

# login:
# 	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

# push:
# 	docker push $(ecr_repo):0.7.9
