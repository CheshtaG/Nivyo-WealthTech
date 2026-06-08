from aws_cdk import CfnOutput, Stack
from constructs import Construct

from components.network import NetworkLayout
from components.network_security import NetworkSecurity
from components.observability import NetworkObservability
from config.models import AppConfig


class VpcStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: AppConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.network = NetworkLayout(self, "Network", config=config)
        self.security = NetworkSecurity(self, "NetworkSecurity", config=config, network=self.network)
        self.observability = NetworkObservability(
            self,
            "NetworkObservability",
            config=config,
            network=self.network,
        )

        CfnOutput(self, "VpcId", value=self.network.vpc.ref, export_name=f"{construct_id}-VpcId")
        CfnOutput(
            self,
            "PublicSubnetIds",
            value=",".join(subnet.ref for subnet in self.network.public_subnets),
            export_name=f"{construct_id}-PublicSubnetIds",
        )
        CfnOutput(
            self,
            "PrivateSubnetIds",
            value=",".join(subnet.ref for subnet in self.network.private_subnets),
            export_name=f"{construct_id}-PrivateSubnetIds",
        )
        CfnOutput(
            self,
            "LambdaSecurityGroupId",
            value=self.security.lambda_security_group.attr_group_id,
            export_name=f"{construct_id}-LambdaSecurityGroupId",
        )
        if self.security.endpoint_security_group is not None:
            CfnOutput(
                self,
                "VpcEndpointSecurityGroupId",
                value=self.security.endpoint_security_group.attr_group_id,
                export_name=f"{construct_id}-VpcEndpointSecurityGroupId",
            )
        if self.observability.flow_log_group is not None:
            CfnOutput(
                self,
                "VpcFlowLogGroupName",
                value=self.observability.flow_log_group.log_group_name,
                export_name=f"{construct_id}-VpcFlowLogGroupName",
            )
