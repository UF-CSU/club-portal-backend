FROM hashicorp/terraform:1.8.3
LABEL maintainer="web@ikehunter.dev"

RUN apk add --update jq kubectl aws-cli

COPY . /infra
WORKDIR /infra
    
ENTRYPOINT ["/bin/terraform"]