ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/jobs-operator

.PHONY: build buildx push tag apply
build:
	docker build -t jobs-operator .

buildx:
	docker buildx build -t jobs-operator . --platform linux/amd64 --load

tag:
	docker tag jobs-operator:latest $(ecr_repo):0.0.1

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):0.0.1

apply:
	kubectl apply -f ./manifests/

