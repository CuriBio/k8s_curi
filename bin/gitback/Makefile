image = gitback
ecr_repo = 245339368379.dkr.ecr.us-east-2.amazonaws.com/$(image)

.PHONY: build buildx push tag apply
build:
	docker build -t $(image) .

buildx:
	docker buildx build -t $(image) . --platform linux/amd64 --load

tag:
	docker tag $(image):latest $(ecr_repo):latest

login:
	aws ecr get-login-password --region us-east-2 | docker login --password-stdin --username AWS $(ecr_repo)

push:
	docker push $(ecr_repo):latest

apply:
	kubectl apply -f ./manifests/

clean:
	docker system prune -a --volumes -f
