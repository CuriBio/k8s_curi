# Tanner (5/23/24): pinning to 3.19 until this issue is resolved https://github.com/alpinelinux/docker-alpine/issues/396
FROM alpine:3.19
RUN apk add --no-cache --update curl python3 py3-pip aws-cli

# currently not switching to non-root user for this image

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"; \
    mv kubectl /usr/local/bin/kubectl; \
    chmod +x /usr/local/bin/kubectl; \
    curl -LO "https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/download/v0.5.9/aws-iam-authenticator_0.6.11_linux_amd64"; \
    mv aws-iam-authenticator_0.6.11_linux_amd64 /usr/local/bin/aws-iam-authenticator; \
    chmod +x /usr/local/bin/aws-iam-authenticator;
