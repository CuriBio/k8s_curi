ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/mantarray

.PHONY: build buildx push tag apply
build:
	docker build -t mantarray .

buildx:
	docker buildx build -t mantarray . --platform linux/amd64 --load

tag:
	docker tag mantarray:latest $(ecr_repo):latest

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):latest

apply:
	kubectl apply -f ./manifests/
