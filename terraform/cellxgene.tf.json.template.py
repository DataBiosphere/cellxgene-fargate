import json

from cellxgene.deployment import (
    emit_tf,
)

num_zones = 2  # An ALB needs at least two availability zones

# List of port forwardings by the network load balancer (NLB). The first element in the tuple is the port on the
# external interface of the NLB, the second element is the port on the instance the the NLB forwards to.
#
ext_port = 80
int_port = 5005

vpc_cidr = "172.111.0.0/16"


def subnet_name(public: bool):
    return 'public' if public else 'private'


def subnet_number(zone: int, public: bool):
    # Even numbers for private subnets, odd numbers for public subnets. The advantage of this numbering scheme is
    # that it won't be perturbed by adding zones.
    return 2 * zone + int(public)


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

# noinspection PyInterpreter
emit_tf({
    "provider": {
        "aws": {
            "region": "us-east-1"
        }
    },
    "data": {
        "aws_availability_zones": {
            "available": {}
        },
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
        "aws_route_table": {
            "cellxgene": {
                "vpc_id": "${aws_vpc.cellxgene.id}",
                "route": [
                    {
                        "cidr_block": "0.0.0.0/0",
                        "egress_only_gateway_id": None,
                        "gateway_id": None,
                        "nat_gateway_id": None,
                        "instance_id": None,
                        "ipv6_cidr_block": None,
                        "network_interface_id": None,
                        "transit_gateway_id": None,
                        "vpc_peering_connection_id": None
                    }
                ],
                "tags": {
                    "Name": "cellxgene"
                }
            }
        },
        "aws_route_table_association": {
            f"cellxgene_{zone}": {
                "route_table_id": f"${{aws_route_table.cellxgene.id}}",
                "subnet_id": f"${{aws_subnet.cellxgene_private_{zone}.id}}"
            } for zone in range(num_zones)
        },
        "aws_security_group": {
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
                        "cidr_blocks": ["0.0.0.0/0"],
                        "protocol": "tcp",
                        "from_port": 80,
                        "to_port": 80
                    },
                    {
                        **ingress_egress_block,
                        "ipv6_cidr_blocks": ["::/0"],
                        "protocol": "tcp",
                        "from_port": 80,
                        "to_port": 80
                    },
                    {
                        **ingress_egress_block,
                        "security_groups": [
                            "${aws_security_group.cellxgene.id}"
                        ],
                        "protocol": "-1",
                        "from_port": 0,
                        "to_port": 0
                    }
                ]
            }
        },
        "aws_ecs_cluster": {
            "cellxgene": {
                "name": "cellxgene",
                "capacity_providers": [
                    "FARGATE",
                    "FARGATE_SPOT"
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
                    "container_name": "cellxgene-container",
                    "container_port": 5005,
                }
            }
        },
        "aws_ecs_task_definition": {
            "cellxgene": {
                "family": "cellxgene",
                "container_definitions": json.dumps(
                    [
                        {
                            "name": "cellxgene-container",
                            "image": "122796619775.dkr.ecr.us-east-1.amazonaws.com/cellxgene-fargate:latest",
                            "cpu": 1,
                            "memory": 2048,
                            "essential": True,
                            "portMappings": [
                                {"containerPort": 5005, "hostPort": 5005}
                            ]
                        }
                    ]
                )
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
                    "${aws_security_group.cellxgene.id}"
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
                        "target_group_arn": "${aws_lb_target_group.cellxgene.id}",
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
                "protocol": "TCP",
                "target_type": "ip",
                "stickiness": {
                    "type": "lb_cookie",
                    "enabled": False
                },
                "vpc_id": "${aws_vpc.cellxgene.id}"
            }
        },
        "aws_lb_target_group_attachment": {
            "cellxgene": {
                "target_group_arn": "${aws_lb_target_group.cellxgene.arn}",
                "target_id": "${aws_ecs_task_definition.cellxgene}",
                "port": 5005
            }
        },
        "aws_network_interface": {
            "cellxgene": {
                "subnet_id": "${aws_subnet.cellxgene_private_0.id}",
                "security_groups": [
                    "${aws_security_group.cellxgene.id}"
                ],
                "tags": {
                    "Name": "cellxgene"
                }
            }
        },
    }
})