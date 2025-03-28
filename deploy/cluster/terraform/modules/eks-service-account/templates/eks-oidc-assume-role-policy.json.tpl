{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "${oidc_provider_arn}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${oidc_uri}:aud": "sts.amazonaws.com",
          "${oidc_uri}:sub": [
            "system:serviceaccount:${service_account_namespace}:${service_account_name}"
          ]
        }
      }
    },
    {
      "Sid": "AllowEksAuthToAssumeRoleForPodIdentity",
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession",
        "sts:AssumeRoleWithWebIdentity"
      ]
    }
  ]
}
