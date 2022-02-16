kind: Deployment
apiVersion: apps/v1
metadata:
  name: ${deployment_name}
  labels:
    app: ${deployment_name}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${deployment_name}
  template:
    metadata:
      labels:
        app: ${deployment_name}
        version: latest
    spec:
      containers:
