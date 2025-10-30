FROM rust:alpine AS builder
RUN apk update && apk add --no-cache openssl \
    openssl-dev \
    openssl-libs-static \
    perl \
    musl-dev

WORKDIR /build
COPY . .
ENV OPENSSL_STATIC=1
RUN cargo install --path .

FROM alpine
RUN apk update && apk add --no-cache openssl \
    libarchive-tools \
    zstd \
    aws-cli

WORKDIR /app
RUN adduser -D app_user
RUN chown -R app_user:app_user /app

COPY --from=builder --chown=app_user:app_user /build/target/release/gitback .

USER app_user
CMD [ "./gitback" ]
