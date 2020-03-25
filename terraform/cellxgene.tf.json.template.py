import json
import os
import re

import boto3
from typing import (
    NamedTuple,
)

from azul.deployment import (
    aws,
    emit_tf,
)

num_zones = 2  # An ALB needs at least two availability zones

# List of port forwardings by the network load balancer (NLB). The first element
# in the tuple is the port on the external interface of the NLB, the second
# element is the port on the instance the the NLB forwards to.
#
ext_port = 80
int_port = 5005

vpc_cidr = "172.111.0.0/16"

zone_name = os.environ['CELLXGENE_ZONE_NAME']
domain_name = os.environ['CELLXGENE_DOMAIN_NAME']

ingress_egress_block = {
    "cidr_blocks": None,
    "ipv6_cidr_blocks": None,
    "prefix_list_ids": None,
    "from_port": None,
    "protocol": None,
    "security_groups": None,
    "self": None,
    "to_port": None,
    "description": None,
}


def subnet_name(public: bool):
    return 'public' if public else 'private'


def subnet_number(zone: int, public: bool):
    # Even numbers for private subnets, odd numbers for public subnets. The
    # advantage of this numbering scheme is that it won't be perturbed by adding
    # zones.
    return 2 * zone + int(public)


class MatrixFile(NamedTuple):
    key: str
    size: int
    study_name: str
    public_url: str
    subdomain: str
    tfid: str
    slug_prefix = '2020-mar-'

    @staticmethod
    def for_key(key: str, size: int) -> 'MatrixFile':
        prefix, _, filename = key.rpartition('/')
        study_name, _, suffix = filename.partition('_')
        # https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/DomainNameFormat.html
        # has nothing against - and _ at the beginning/end or repeating them but
        # we'll enforce those things anyways.
        assert re.fullmatch(r'[a-z0-9]+([-_][a-z0-9]+)*', study_name, re.I), study_name
        assert len(study_name) < 64
        return MatrixFile(key=key,
                          size=size,
                          study_name=study_name,
                          public_url='https://data.humancellatlas.org/' + key,
                          subdomain=study_name.lower(),
                          tfid='cellxgene_' + study_name.replace('-', '_').lower())

    @property
    def slug(self):
        assert self.subdomain.startswith(self.slug_prefix)
        return self.subdomain[len(self.slug_prefix):]

    @property
    def estimated_memory_requirement_in_mib(self):
        return 2048 if self.size < 10 ** 9 else 4 * 1024


def matrix_files():
    bucket = boto3.resource('s3').Bucket('release-files.data.humancellatlas.org')
    for obj in bucket.objects.filter(Prefix='release-files/releases/2020-mar/'):
        if obj.key.endswith('.h5ad'):
            yield MatrixFile.for_key(obj.key, obj.size)


matrix_files = list(matrix_files())

assert len(set(m.subdomain for m in matrix_files)) == len(matrix_files)
assert len(set(m.tfid for m in matrix_files)) == len(matrix_files)

emit_tf({
    "data": {
        "aws_availability_zones": {
            "available": {}
        },
        "aws_ecr_repository": {
            "cellxgene": {
                "name": os.environ['CELLXGENE_IMAGE']
            }
        },
        "aws_ecr_image": {
            "cellxgene": {
                "repository_name": "${data.aws_ecr_repository.cellxgene.name}",
                "image_tag": os.environ['CELLXGENE_VERSION']
            }
        },
        "aws_route53_zone": {
            "cellxgene": {
                "name": zone_name + ".",
                "private_zone": False
            }
        },
        "aws_iam_role": {
            "cellxgene": {
                "name": "ecsTaskExecutionRole"
            }
        }
    },
    "resource": {
        "aws_vpc": {
            "cellxgene": {
                "cidr_block": vpc_cidr,
                "tags": {
                    "Name": "cellxgene"
                }
            }
        },
        "aws_subnet": {  # a public and a private subnet per availability zone
            f"cellxgene_{subnet_name(public)}_{zone}": {
                "availability_zone": f"${{data.aws_availability_zones.available.names[{zone}]}}",
                "cidr_block": f"${{cidrsubnet(aws_vpc.cellxgene.cidr_block, 8, {subnet_number(zone, public)})}}",
                "map_public_ip_on_launch": public,
                "vpc_id": "${aws_vpc.cellxgene.id}",
                "tags": {
                    "Name": f"cellxgene-{subnet_name(public)}-{subnet_number(zone, public)}"
                }
            } for public in (False, True) for zone in range(num_zones)
        },
        "aws_internet_gateway": {
            "cellxgene": {
                "vpc_id": "${aws_vpc.cellxgene.id}",
                "tags": {
                    "Name": "cellxgene"
                }
            }
        },
        "aws_route": {
            "cellxgene": {
                "destination_cidr_block": "0.0.0.0/0",
                "gateway_id": "${aws_internet_gateway.cellxgene.id}",
                "route_table_id": "${aws_vpc.cellxgene.main_route_table_id}"
            }
        },
        "aws_eip": {
            f"cellxgene_{zone}": {
                "depends_on": [
                    "aws_internet_gateway.cellxgene"
                ],
                "vpc": True,
                "tags": {
                    "Name": f"cellxgene-{zone}"
                }
            } for zone in range(num_zones)
        },
        "aws_nat_gateway": {
            f"cellxgene_{zone}": {
                "allocation_id": f"${{aws_eip.cellxgene_{zone}.id}}",
                "subnet_id": f"${{aws_subnet.cellxgene_public_{zone}.id}}",
                "tags": {
                    "Name": f"cellxgene-{zone}"
                }
            } for zone in range(num_zones)
        },
        "aws_route_table": {
            f"cellxgene_{zone}": {
                "route": [
                    {
                        "cidr_block": "0.0.0.0/0",
                        "nat_gateway_id": f"${{aws_nat_gateway.cellxgene_{zone}.id}}",
                        "egress_only_gateway_id": None,
                        "gateway_id": None,
                        "instance_id": None,
                        "ipv6_cidr_block": None,
                        "network_interface_id": None,
                        "transit_gateway_id": None,
                        "vpc_peering_connection_id": None
                    }
                ],
                "vpc_id": "${aws_vpc.cellxgene.id}",
                "tags": {
                    "Name": f"cellxgene-{zone}"
                }
            } for zone in range(num_zones)
        },
        "aws_route_table_association": {
            f"cellxgene_{zone}": {
                "route_table_id": f"${{aws_route_table.cellxgene_{zone}.id}}",
                "subnet_id": f"${{aws_subnet.cellxgene_private_{zone}.id}}"
            } for zone in range(num_zones)
        },
        "aws_security_group": {
            "cellxgene_alb": {
                "name": "cellxgene-alb",
                "vpc_id": "${aws_vpc.cellxgene.id}",
                "egress": [
                    {
                        **ingress_egress_block,
                        "cidr_blocks": ["0.0.0.0/0"],
                        "protocol": -1,
                        "from_port": 0,
                        "to_port": 0
                    }
                ],
                "ingress": [
                    {
                        **ingress_egress_block,
                        "cidr_blocks": ["0.0.0.0/0"],
                        "protocol": "tcp",
                        "from_port": ext_port,
                        "to_port": ext_port
                    }
                ]
            },
            "cellxgene": {
                "name": "cellxgene",
                "vpc_id": "${aws_vpc.cellxgene.id}",
                "egress": [
                    {
                        **ingress_egress_block,
                        "cidr_blocks": ["0.0.0.0/0"],
                        "protocol": -1,
                        "from_port": 0,
                        "to_port": 0
                    }
                ],
                "ingress": [
                    {
                        **ingress_egress_block,
                        "from_port": int_port,
                        "protocol": "tcp",
                        "security_groups": [
                            "${aws_security_group.cellxgene_alb.id}"
                        ],
                        "to_port": int_port,
                    }
                ]
            }
        },
        "aws_lb": {
            "cellxgene": {
                "name": "cellxgene",
                "load_balancer_type": "application",
                "subnets": [
                    f"${{aws_subnet.cellxgene_public_{zone}.id}}" for zone in range(num_zones)
                ],
                "security_groups": [
                    "${aws_security_group.cellxgene_alb.id}"
                ],
                "tags": {
                    "Name": "cellxgene"
                }
            }
        },
        "aws_lb_listener": {
            "cellxgene": {
                "port": ext_port,
                "protocol": "HTTP",
                "default_action": {
                    "type": "fixed-response",
                    "fixed_response": {
                        "content_type": "text/html",
                        # This has to be <= 1024 bytes, hence the JavaScript approach
                        "message_body":
                            f"<html><body><script>"
                            f"var l={[m.slug for m in matrix_files]};"
                            f"for(i=0;i<l.length;i++)"
                            f"document.write("
                            f"'<p><a href=\"http://{MatrixFile.slug_prefix}'+l[i]+'.{domain_name}\">'+l[i]+'</a></p>'"
                            f");"
                            f"</script></body></html>",
                        "status_code": "200"
                    }
                },
                "load_balancer_arn": "${aws_lb.cellxgene.id}"
            }
        },
        "aws_lb_listener_rule": {
            m.tfid: {
                "listener_arn": "${aws_lb_listener.cellxgene.arn}",
                "action": {
                    "type": "forward",
                    "target_group_arn": f"${{aws_lb_target_group.{m.tfid}.arn}}"
                },
                "condition": {
                    "host_header": {
                        "values": [
                            f"{m.subdomain}.{domain_name}"
                        ]
                    }
                },
                "depends_on": [f"aws_lb_target_group.{m.tfid}"]
            } for m in matrix_files
        },
        "aws_lb_target_group": {
            m.tfid: {
                "port": int_port,
                "protocol": "HTTP",
                "target_type": "ip",
                "stickiness": {
                    # Stickyness is irrelevant when there is only one target but
                    # should be reconsidered when we load balance over multiple
                    # containers.
                    "enabled": False,
                    "type": "lb_cookie",
                },
                "health_check": {
                    "protocol": "HTTP",
                    "path": "/",
                    "port": "traffic-port",
                    "healthy_threshold": 2,
                    # This and `interval` give the containers for the large files enough time to initialize
                    "unhealthy_threshold": 10,
                    "timeout": 30,
                    "interval": 60,
                    "matcher": "200"
                },
                "vpc_id": "${aws_vpc.cellxgene.id}",
                "tags": {
                    # Work around TF bug with eplicit name. This will make TF chose a name for us:
                    # https://github.com/terraform-providers/terraform-provider-aws/issues/636#issuecomment-397459646
                    "Name": m.subdomain
                }
            } for m in matrix_files
        },
        "aws_ecs_cluster": {
            "cellxgene": {
                "name": "cellxgene",
                "capacity_providers": [
                    "FARGATE"
                ]
            }
        },
        "aws_ecs_service": {
            m.tfid: {
                "name": f"cellxgene-{m.subdomain}",
                "cluster": "${aws_ecs_cluster.cellxgene.id}",
                "task_definition": f"${{aws_ecs_task_definition.{m.tfid}.arn}}",
                "desired_count": 1,
                "launch_type": "FARGATE",
                "load_balancer": {
                    "target_group_arn": f"${{aws_lb_target_group.{m.tfid}.arn}}",
                    "container_name": "cellxgene",
                    "container_port": int_port,
                },
                "network_configuration": {
                    "subnets": [
                        f"${{aws_subnet.cellxgene_private_{zone}.id}}"
                        for zone in range(num_zones)
                    ],
                    "security_groups": [
                        "${aws_security_group.cellxgene.id}"
                    ]
                }
            } for m in matrix_files
        },
        "aws_route53_record": {
            'cellxgene' if m is None else m.tfid: {
                "zone_id": "${data.aws_route53_zone.cellxgene.id}",
                "name": 'cellxgene' if m is None else m.subdomain + '.' + domain_name,
                "type": "A",
                "alias": {
                    "name": "${aws_lb.cellxgene.dns_name}",
                    "zone_id": "${aws_lb.cellxgene.zone_id}",
                    "evaluate_target_health": False
                }
            } for m in [None, *matrix_files]
        },
        "aws_ecs_task_definition": {
            m.tfid: {
                "family": m.tfid,
                "requires_compatibilities": [
                    "FARGATE"
                ],
                "network_mode": "awsvpc",
                "cpu": 1024,
                # 1 vCPU (https://docs.aws.amazon.com/AmazonECS/latest/userguide/fargate-task-defs.html)
                "memory": m.estimated_memory_requirement_in_mib,
                "container_definitions": json.dumps(
                    [
                        {
                            "name": "cellxgene",
                            "image": "${data.aws_ecr_repository.cellxgene.repository_url}"
                                     "@${data.aws_ecr_image.cellxgene.image_digest}",
                            "essential": True,
                            "command": [
                                "launch",
                                "--verbose",
                                "--backed",
                                m.public_url,
                                "--host=0.0.0.0",
                                f"--port={int_port}"
                            ],
                            "portMappings": [
                                {"containerPort": int_port, "hostPort": int_port}
                            ],
                            "logConfiguration": {
                                "logDriver": "awslogs",
                                "options": {
                                    "awslogs-group": "${aws_cloudwatch_log_group.cellxgene.name}",
                                    "awslogs-region": aws.region_name,
                                    "awslogs-stream-prefix": m.subdomain
                                }
                            }
                        }
                    ]
                ),
                "execution_role_arn": "${data.aws_iam_role.cellxgene.arn}"
            } for m in matrix_files
        },
        "aws_cloudwatch_log_group": {
            "cellxgene": {
                "name": "/aws/fargate/cellxgene"
            }
        },
    }
})
