#!/bin/bash

tablename="clubmanager-tf-state-lock"
bucketname="clubmanager-terraform-state"

aws dynamodb create-table \
    --table-name $tablename \
    --attribute-definitions \
        AttributeName=LockID,AttributeType=S \
    --key-schema \
        AttributeName=LockID,KeyType=HASH \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --table-class STANDARD > /dev/null
    
aws s3api create-bucket \
    --bucket $bucketname \
    --region us-east-1 > /dev/null
