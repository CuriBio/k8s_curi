apiVersion: v1
kind: Service
metadata:
  name: ${service_name}
spec:
  ports:
  - name: http
    targetPort: 8000
    port: 80
  type: ClusterIP
  selector:
    app: ${deployment_name}