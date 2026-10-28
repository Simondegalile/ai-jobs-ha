#!/bin/bash
set -e

CLUSTER=$1
if [ "$CLUSTER" != "cluster-a" ] && [ "$CLUSTER" != "cluster-b" ]; then
  echo "Usage : sudo ./deploy.sh cluster-a | cluster-b"
  exit 1
fi

if ! command -v curl > /dev/null; then
  apt-get install -y curl
fi

if ! command -v docker > /dev/null; then
  apt-get update
  apt-get install -y docker.io
fi

docker build -t ai-jobs-dashboard:1.0 .
docker save ai-jobs-dashboard:1.0 -o /tmp/ai-jobs-dashboard.tar
microk8s ctr image import /tmp/ai-jobs-dashboard.tar

microk8s kubectl apply -f k8s/base/namespace.yaml
microk8s kubectl apply -f k8s/$CLUSTER/configmap.yaml
microk8s kubectl apply -f k8s/base/secret.yaml
microk8s kubectl apply -f k8s/base/deployment.yaml
microk8s kubectl apply -f k8s/base/service.yaml
microk8s kubectl apply -f k8s/$CLUSTER/ingress.yaml
microk8s kubectl apply -f k8s/base/statefulset.yaml
microk8s kubectl apply -f k8s/base/daemonset.yaml
microk8s kubectl apply -f k8s/base/jobs.yaml

microk8s kubectl rollout status deployment/ai-jobs -n ai-jobs --timeout=180s
microk8s kubectl get all -n ai-jobs -o wide
curl -s http://localhost:30080/health
echo
curl -s http://localhost:30080/api/stats
echo
