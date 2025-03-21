#!/bin/sh

set -e

kubectl delete -f . --grace-period=0 --force --wait=false

helm uninstall redis --namespace redis
helm uninstall external-secrets --namespace external-secrets
