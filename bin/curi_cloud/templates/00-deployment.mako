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
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
 name: ${deployment_name}-ingress
 annotations:
   kubernetes.io/ingress.class: "nginx"
   ####nginx.org/rewrites: "serviceName=${service_name} rewrite=/"
status:
  loadBalancer:
    ingress:
    - {}
spec:
 rules:
 - host: ???
   http:
    paths:
