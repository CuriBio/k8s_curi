# TODO ADD YOUR ECR REPO URL
ecr_repo = 077346344852.dkr.ecr.us-east-2.amazonaws.com/pheno/apiv1

.PHONY: build buildx push tag apply
build:
	docker build -t apiv1 .

buildx:
	docker buildx build -t apiv1 . --platform linux/amd64 --load

tag:
	docker tag apiv1:latest $(ecr_repo):latest

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):latest

apply:
	kubectl apply -f ./manifests/

