apiVersion: v1
kind: Service
metadata:
  name: ${service_name}
spec:
  ports:
  - name: http
    targetPort: 8000
    port: 80
  type: NodePort
  selector:
    app: ${deployment_name}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
 name: bar-ingress
 annotations:
   kubernetes.io/ingress.class: "nginx"
   nginx.org/rewrites: "serviceName=${service_name} rewrite=/"
spec:
 rules:
 - host: ???
   http:
     paths:
     - path: /
       pathType: Prefix
       backend:
         service:
           name: ${service_name}
           port:
             number: 80
