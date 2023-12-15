FROM node:16.17.0

# ARG CLUSTER
# ENV CLUSTER=$CLUSTER


# ARG ACCESS_KEY
# ARG ACCESS_KEY_ID
# ENV AWS_SECRET_ACCESS_KEY=$ACCESS_KEY
# ENV AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID


RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-boto3 awscli

WORKDIR /app
COPY ./frontend/pulse3d/src ./src
COPY ./frontend/pulse3d/upload_fe_s3.py ./

RUN cd src/ && npm i && npm run export:modl
RUN python3 upload_fe_s3.py modl