import base64
from subprocess import run

import boto3

ecr = boto3.client('ecr')
response = ecr.get_authorization_token()
auth = response['authorizationData'][0]
url = auth['proxyEndpoint']
token = base64.b64decode(auth['authorizationToken'])
_, _, password = token.partition(b':')
run(['docker', 'login', '--username', 'AWS', '--password-stdin', url], input=password)
print('Expiration:', auth['expiresAt'])
