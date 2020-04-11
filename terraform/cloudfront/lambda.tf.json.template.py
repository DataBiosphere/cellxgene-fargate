import json

from azul.deployment import (
    emit_tf,
)

emit_tf({
    'data': {
        'aws_cloudfront_distribution': {
            'cloudfront': {
                'id': 'E3QDNPF7XH7O7G'
            }
        }
    },
    'resource': {
        'aws_iam_role': {
            'cloudfront': {
                'name': 'cellxgene-cloudfront',
                'assume_role_policy': json.dumps({
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {
                                'Service': [
                                    'lambda.amazonaws.com',
                                    'edgelambda.amazonaws.com'
                                ]
                            },
                            'Action': 'sts:AssumeRole'
                        }
                    ]
                })
            }
        },
        'aws_iam_policy': {
            'cloudfront': {
                'name': 'cellxgene-cloudfront',
                'path': '/',
                'policy': json.dumps({
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Action': [
                                'logs:CreateLogGroup',
                                'logs:CreateLogStream',
                                'logs:PutLogEvents'
                            ],
                            'Resource': 'arn:aws:logs:*:*:*',
                            'Effect': 'Allow'
                        }
                    ]
                })
            }
        },
        'aws_iam_role_policy_attachment': {
            'cloudfront': {
                'role': '${aws_iam_role.cloudfront.name}',
                'policy_arn': '${aws_iam_policy.cloudfront.arn}'
            }
        },
        'aws_lambda_function': {
            'cloudfront': {
                'function_name': 'cellxgene-cloudfront',
                'runtime': 'python3.7',
                'handler': 'app.lambda_handler',
                'filename': 'package.zip',
                'role': '${aws_iam_role.cloudfront.arn}',
                'source_code_hash': '${filebase64sha256("package.zip")}',
                'publish': True,
                'provider': 'aws.us-east-1'
            }
        }
    }
})
