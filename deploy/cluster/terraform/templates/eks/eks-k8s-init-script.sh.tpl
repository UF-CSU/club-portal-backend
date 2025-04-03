#!/bin/bash

# set -e

aws eks update-kubeconfig --region ${cluster_region} --name ${cluster_name}

kubectl create namespace ${cluster_main_namespace} --dry-run=client -o yaml | kubectl apply -f -

kubectl create namespace ${cluster_secretsmanager_namespace} --dry-run=client -o yaml | kubectl apply -f -
kubectl create serviceaccount ${cluster_secretsmanager_sa_name} -n ${cluster_secretsmanager_namespace} --dry-run=client -o yaml | kubectl apply -f -
kubectl annotate serviceaccount ${cluster_secretsmanager_sa_name} -n ${cluster_secretsmanager_namespace} eks.amazonaws.com/role-arn=${cluster_secretsmanager_sa_role_arn} --overwrite

kubectl create namespace ${external_dns_namespace} --dry-run=client -o yaml | kubectl apply -f -
kubectl create serviceaccount ${external_dns_sa_name} -n ${external_dns_namespace} --dry-run=client -o yaml | kubectl apply -f -
kubectl annotate serviceaccount ${external_dns_sa_name} -n ${external_dns_namespace} eks.amazonaws.com/role-arn=${external_dns_sa_role_arn} --overwrite
kubectl annotate serviceaccount ${external_dns_sa_name} -n ${external_dns_namespace} app.kubernetes.io/name=external-dns --overwrite

