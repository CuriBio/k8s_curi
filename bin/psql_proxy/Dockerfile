FROM alpine:latest
RUN apk add --no-cache --update curl

RUN useradd main_user && groupadd main_group
USER main_user:main_group

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"; \
    mv kubectl /usr/local/bin/kubectl; \
    chmod +x /usr/local/bin/kubectl; \
    curl -LO "https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/download/v0.5.9/aws-iam-authenticator_0.5.9_linux_amd64"; \
    mv aws-iam-authenticator_0.5.9_linux_amd64 /usr/local/bin/aws-iam-authenticator; \
    chmod +x /usr/local/bin/aws-iam-authenticator;
