from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

from components.network import NetworkLayout
from config.models import AppConfig, SecurityGroupConfig, SecurityGroupRuleConfig


class NetworkSecurity(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: AppConfig,
        network: NetworkLayout,
    ) -> None:
        super().__init__(scope, construct_id)

        region = Stack.of(self).region
        network_cfg = config.network

        self.endpoint_security_group = None
        if network_cfg.vpc_endpoints.bedrock_interface.enabled:
            endpoint_sg = network_cfg.security_groups.vpc_endpoints_sg
            self.endpoint_security_group = self._create_security_group(
                "VpcEndpointSecurityGroup",
                security_group=endpoint_sg,
                vpc_id=network.vpc.ref,
            )

        lambda_sg = network_cfg.security_groups.lambda_sg
        self.lambda_security_group = self._create_security_group(
            "LambdaSecurityGroup",
            security_group=lambda_sg,
            vpc_id=network.vpc.ref,
        )

        if network_cfg.vpc_endpoints.s3_gateway.enabled:
            ec2.CfnVPCEndpoint(
                self,
                "S3GatewayEndpoint",
                vpc_id=network.vpc.ref,
                service_name=f"com.amazonaws.{region}.s3",
                vpc_endpoint_type="Gateway",
                route_table_ids=[route_table.ref for route_table in network.private_route_tables],
            )

        for service_suffix in network_cfg.vpc_endpoints.bedrock_interface.services:
            ec2.CfnVPCEndpoint(
                self,
                self._endpoint_id(service_suffix),
                vpc_id=network.vpc.ref,
                service_name=f"com.amazonaws.{region}.{service_suffix}",
                vpc_endpoint_type="Interface",
                private_dns_enabled=True,
                subnet_ids=[subnet.ref for subnet in network.private_subnets],
                security_group_ids=[self.endpoint_security_group.attr_group_id],
            )

    def _create_security_group(
        self,
        construct_id: str,
        *,
        security_group: SecurityGroupConfig,
        vpc_id: str,
    ) -> ec2.CfnSecurityGroup:
        return ec2.CfnSecurityGroup(
            self,
            construct_id,
            group_description=security_group.description,
            vpc_id=vpc_id,
            security_group_ingress=[
                self._to_ingress(rule) for rule in security_group.ingress_rules
            ],
            security_group_egress=[
                self._to_egress(rule) for rule in security_group.egress_rules
            ],
            tags=[{"key": "Name", "value": security_group.name}],
        )

    def _to_ingress(self, rule: SecurityGroupRuleConfig) -> ec2.CfnSecurityGroup.IngressProperty:
        return self._build_rule_property(
            rule,
            ec2.CfnSecurityGroup.IngressProperty,
        )

    def _to_egress(self, rule: SecurityGroupRuleConfig) -> ec2.CfnSecurityGroup.EgressProperty:
        return self._build_rule_property(
            rule,
            ec2.CfnSecurityGroup.EgressProperty,
        )

    def _build_rule_property(self, rule: SecurityGroupRuleConfig, property_type: type):
        kwargs = {
            "ip_protocol": rule.protocol,
            "cidr_ip": rule.cidr,
            "description": rule.description,
        }
        if rule.protocol != "-1":
            kwargs["from_port"] = rule.from_port
            kwargs["to_port"] = rule.to_port
        return property_type(**kwargs)

    def _endpoint_id(self, service_suffix: str) -> str:
        return "".join(part.title() for part in service_suffix.split("-")) + "Endpoint"
