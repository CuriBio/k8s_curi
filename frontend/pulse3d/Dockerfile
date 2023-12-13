FROM node:16.17.0

ARG CLUSTER
ENV CLUSTER=$CLUSTER

RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-boto3

WORKDIR /app
COPY ./frontend/pulse3d/src ./src
COPY ./frontend/pulse3d/upload_fe_s3.py ./

RUN cd src/ && npm i && npm run export:$CLUSTER
RUN python upload_fe_s3.py $CLUSTER