import json
import os

from azul.collections import dict_merge
from azul.deployment import (
    aws,
    emit_tf,
)
from azul.strings import departition

num_zones = 2  # An ALB needs at least two availability zones

# List of port forwardings by the network load balancer (NLB). The first element
# in the tuple is the port on the external interface of the NLB, the second
# element is the port on the instance the the NLB forwards to.
#
ext_port = 80
int_port = 5005

vpc_cidr = "172.111.0.0/16"

domain_name = 'singlecell.gi.ucsc.edu'

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
                "name": domain_name + ".",
                "private_zone": False
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
                "default_action": [
                    {
                        "target_group_arn": "${aws_lb_target_group.cellxgene.arn}",
                        "type": "forward"
                    }
                ],
                "load_balancer_arn": "${aws_lb.cellxgene.id}"
            }
        },
        "aws_lb_target_group": {
            "cellxgene": {
                "name": "cellxgene",
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
                "vpc_id": "${aws_vpc.cellxgene.id}"
            }
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
            "cellxgene": {
                "name": "cellxgene",
                "cluster": "${aws_ecs_cluster.cellxgene.id}",
                "task_definition": "${aws_ecs_task_definition.cellxgene.arn}",
                "desired_count": 1,
                "launch_type": "FARGATE",
                "load_balancer": {
                    "target_group_arn": "${aws_lb_target_group.cellxgene.arn}",
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
            }
        },
        "aws_route53_record": {
            **dict_merge(
                {
                    departition('cellxgene', '_', subdomain): {
                        "zone_id": "${data.aws_route53_zone.cellxgene.id}",
                        "name": departition(subdomain, '.', f"cellxgene.{domain_name}"),
                        "type": "A",
                        "alias": {
                            "name": "${aws_lb.cellxgene.dns_name}",
                            "zone_id": "${aws_lb.cellxgene.zone_id}",
                            "evaluate_target_health": False
                        }
                    }
                } for i, subdomain in enumerate(['example'])),
        },
        "aws_ecs_task_definition": {
            "cellxgene": {
                "family": "cellxgene",
                "requires_compatibilities": [
                    "FARGATE"
                ],
                "network_mode": "awsvpc",
                "cpu": 1024,  # 1 vCPU (https://docs.aws.amazon.com/AmazonECS/latest/userguide/fargate-task-defs.html)
                "memory": 2048,
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
                                "https://cellxgene-example-data.czi.technology/pbmc3k.h5ad",
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
                                    "awslogs-stream-prefix": "cellxgene"
                                }
                            }
                        }
                    ]
                ),
                "execution_role_arn": "arn:aws:iam::122796619775:role/ecsTaskExecutionRole"
            }
        },
        "aws_cloudwatch_log_group": {
            "cellxgene": {
                "name": "/aws/fargate/cellxgene"
            }
        },
    }
})
