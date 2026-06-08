from aws_cdk import aws_ec2 as ec2
from constructs import Construct

from config.models import AppConfig


class NetworkLayout(Construct):
    def __init__(self, scope: Construct, construct_id: str, *, config: AppConfig) -> None:
        super().__init__(scope, construct_id)

        network = config.network

        if len(network.public_subnet_cidrs) != network.availability_zones:
            raise ValueError("network.public_subnet_cidrs count must match network.availability_zones")
        if len(network.private_subnet_cidrs) != network.availability_zones:
            raise ValueError("network.private_subnet_cidrs count must match network.availability_zones")
        if len(network.availability_zone_names) != network.availability_zones:
            raise ValueError("network.availability_zone_names count must match network.availability_zones")

        self.vpc = ec2.CfnVPC(
            self,
            "Vpc",
            cidr_block=network.vpc_cidr,
            enable_dns_hostnames=network.enable_dns_hostnames,
            enable_dns_support=network.enable_dns_support,
            tags=[{"key": "Name", "value": network.vpc_name}],
        )

        names = network.resource_names

        internet_gateway = ec2.CfnInternetGateway(
            self,
            "InternetGateway",
            tags=[{"key": "Name", "value": names.internet_gateway}],
        )

        gateway_attachment = ec2.CfnVPCGatewayAttachment(
            self,
            "InternetGatewayAttachment",
            vpc_id=self.vpc.ref,
            internet_gateway_id=internet_gateway.ref,
        )

        self.public_subnets = [
            self._create_subnet(
                f"PublicSubnet{index}",
                subnet_name=names.public_subnets[index - 1],
                cidr_block=cidr_block,
                availability_zone=network.availability_zone_names[index - 1],
                public=True,
            )
            for index, cidr_block in enumerate(network.public_subnet_cidrs, start=1)
        ]

        self.private_subnets = [
            self._create_subnet(
                f"PrivateSubnet{index}",
                subnet_name=names.private_subnets[index - 1],
                cidr_block=cidr_block,
                availability_zone=network.availability_zone_names[index - 1],
                public=False,
            )
            for index, cidr_block in enumerate(network.private_subnet_cidrs, start=1)
        ]

        public_route_table = ec2.CfnRouteTable(
            self,
            "PublicRouteTable",
            vpc_id=self.vpc.ref,
            tags=[{"key": "Name", "value": names.public_route_table}],
        )
        public_default_route = ec2.CfnRoute(
            self,
            "PublicDefaultRoute",
            route_table_id=public_route_table.ref,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=internet_gateway.ref,
        )
        public_default_route.add_dependency(gateway_attachment)

        for index, subnet in enumerate(self.public_subnets, start=1):
            ec2.CfnSubnetRouteTableAssociation(
                self,
                f"PublicSubnet{index}RouteTableAssociation",
                subnet_id=subnet.ref,
                route_table_id=public_route_table.ref,
            )

        nat_gateway = None
        if network.nat_gateway.enabled:
            nat_eip = ec2.CfnEIP(
                self,
                "NatGatewayElasticIp",
                domain="vpc",
                tags=[{"key": "Name", "value": names.nat_elastic_ip}],
            )
            nat_eip.add_dependency(gateway_attachment)

            nat_gateway = ec2.CfnNatGateway(
                self,
                "NatGateway",
                allocation_id=nat_eip.attr_allocation_id,
                subnet_id=self.public_subnets[0].ref,
                tags=[{"key": "Name", "value": names.nat_gateway}],
            )

        self.private_route_tables = []
        for index, subnet in enumerate(self.private_subnets, start=1):
            route_table = ec2.CfnRouteTable(
                self,
                f"PrivateRouteTable{index}",
                vpc_id=self.vpc.ref,
                tags=[{"key": "Name", "value": names.private_route_tables[index - 1]}],
            )
            self.private_route_tables.append(route_table)

            if nat_gateway is not None:
                private_default_route = ec2.CfnRoute(
                    self,
                    f"PrivateDefaultRoute{index}",
                    route_table_id=route_table.ref,
                    destination_cidr_block="0.0.0.0/0",
                    nat_gateway_id=nat_gateway.ref,
                )
                private_default_route.add_dependency(nat_gateway)

            ec2.CfnSubnetRouteTableAssociation(
                self,
                f"PrivateSubnet{index}RouteTableAssociation",
                subnet_id=subnet.ref,
                route_table_id=route_table.ref,
            )

    def _create_subnet(
        self,
        construct_id: str,
        *,
        subnet_name: str,
        cidr_block: str,
        availability_zone: str,
        public: bool,
    ) -> ec2.CfnSubnet:
        return ec2.CfnSubnet(
            self,
            construct_id,
            vpc_id=self.vpc.ref,
            cidr_block=cidr_block,
            availability_zone=availability_zone,
            map_public_ip_on_launch=public,
            tags=[{"key": "Name", "value": subnet_name}],
        )
