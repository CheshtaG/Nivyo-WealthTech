from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct

from components.network import NetworkLayout
from config.cdk_mappings import log_retention_days, removal_policy
from config.models import AppConfig


class NetworkObservability(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: AppConfig,
        network: NetworkLayout,
    ) -> None:
        super().__init__(scope, construct_id)

        flow_logs_cfg = config.observability.vpc_flow_logs
        self.flow_log_group = None

        if not flow_logs_cfg.enabled:
            return

        if flow_logs_cfg.import_existing_log_group:
            self.flow_log_group = logs.LogGroup.from_log_group_name(
                self,
                "VpcFlowLogGroup",
                flow_logs_cfg.log_group_name,
            )
        else:
            self.flow_log_group = logs.LogGroup(
                self,
                "VpcFlowLogGroup",
                log_group_name=flow_logs_cfg.log_group_name,
                retention=log_retention_days(flow_logs_cfg.retention_days),
                removal_policy=removal_policy(flow_logs_cfg.removal_policy),
            )

        flow_logs_role = iam.Role(
            self,
            "VpcFlowLogsRole",
            assumed_by=iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"),
            description="VPC Flow Logs delivery role",
        )
        self.flow_log_group.grant_write(flow_logs_role)

        ec2.CfnFlowLog(
            self,
            "VpcFlowLog",
            deliver_logs_permission_arn=flow_logs_role.role_arn,
            log_destination_type="cloud-watch-logs",
            log_group_name=self.flow_log_group.log_group_name,
            resource_id=network.vpc.ref,
            resource_type="VPC",
            traffic_type=flow_logs_cfg.traffic_type,
        )
