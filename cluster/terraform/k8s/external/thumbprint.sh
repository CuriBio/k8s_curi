#!/bin/bash

set -euo pipefail

HOST="oidc.eks.$1.amazonaws.com"

# https://github.com/terraform-providers/terraform-provider-aws/issues/10104

# echo | openssl s_client -servername "$HOST" -showcerts -connect "$HOST:443" 2>&- \
#   | sed -n '/-----BEGIN CERTIFICATE-----/h;//!H;$!d;x;s/\(.*-----END CERTIFICATE-----\).*/\1/p' \
#   | openssl x509 -fingerprint -sha1 -noout \
#   | tr '[:upper:]' '[:lower:]' \
#   | sed 's/://g; s/.*=\(.*\)/{"thumbprint": "\1"}/'


echo | openssl s_client -servername "$HOST" -connect "$HOST:443" 2>&- \
    | sed -n '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p' \
    | openssl x509 -fingerprint -sha1 -noout \
    | tr '[:upper:]' '[:lower:]' \
    | sed 's/://g; s/.*=\(.*\)/{"thumbprint": "\1"}/'
    #| sed 's/://g' | awk -F= '{print $2}'

