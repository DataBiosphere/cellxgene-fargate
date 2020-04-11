from azul import config
from azul.deployment import (
    aws,
    emit_tf,
)

if config.terraform_component:
    suffix = "-" + config.terraform_component
else:
    suffix = ''

emit_tf(
    {
        "terraform": {
            "backend": {
                "s3": {
                    "bucket": config.terraform_backend_bucket,
                    "key": f"cellxgene-fargate{suffix}.tfstate",
                    "region": aws.region_name,
                    **(
                        {
                            "profile": aws.profile['source_profile'],
                            "role_arn": aws.profile['role_arn']
                        } if 'role_arn' in aws.profile else {
                        }
                    )
                }
            }
        }
    }
)
