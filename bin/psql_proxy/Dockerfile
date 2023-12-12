FROM alpine:latest
RUN apk add --no-cache --update curl python3 py3-pip aws-cli
# RUN pip install awscli

# currently not switching to non-root user for this image

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"; \
    mv kubectl /usr/local/bin/kubectl; \
    chmod +x /usr/local/bin/kubectl; \
    curl -LO "https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/download/v0.5.9/aws-iam-authenticator_0.6.11_linux_amd64"; \
    mv aws-iam-authenticator_0.6.11_linux_amd64 /usr/local/bin/aws-iam-authenticator; \
    chmod +x /usr/local/bin/aws-iam-authenticator;
