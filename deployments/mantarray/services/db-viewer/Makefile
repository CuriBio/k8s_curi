ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/db-viewer

.PHONY: build buildx push tag apply
build:
	docker build -t db-viewer .

buildx:
	docker buildx build -t db-viewer . --platform linux/amd64 --load

tag:
	docker tag db-viewer:latest $(ecr_repo):latest

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):latest

apply:
	kubectl apply -f ./manifests/

