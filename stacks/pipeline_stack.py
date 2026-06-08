from typing import Optional

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from config.models import AppConfig, LambdaFunctionConfig
from stacks.bedrock_stack import BedrockStack
from stacks.iam_stack import IamStack
from stacks.vpc_stack import VpcStack


class PipelineStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: AppConfig,
        vpc_stack: VpcStack,
        iam_stack: IamStack,
        bedrock_stack: BedrockStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        imported_vpc = ec2.Vpc.from_vpc_attributes(
            self,
            "ImportedVpc",
            vpc_id=vpc_stack.network.vpc.ref,
            availability_zones=list(config.network.availability_zone_names),
        )
        private_subnets = [
            ec2.Subnet.from_subnet_id(
                self,
                f"ImportedPrivateSubnet{index}",
                subnet.ref,
            )
            for index, subnet in enumerate(vpc_stack.network.private_subnets, start=1)
        ]
        lambda_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            "ImportedLambdaSecurityGroup",
            vpc_stack.security.lambda_security_group.attr_group_id,
        )

        common_env = {
            "S3_INPUT_BUCKET": config.storage.input_bucket.name,
            "S3_CHUNK_STORE_BUCKET": config.storage.chunk_store_bucket.name,
            "BEDROCK_KB_ID": bedrock_stack.knowledge_base_resources.knowledge_base.attr_knowledge_base_id,
            "BEDROCK_EMBEDDING_MODEL": config.pipeline.embedding_model_id,
            "CHUNK_SIZE": str(config.pipeline.chunk_size),
            "CHUNK_OVERLAP": str(config.pipeline.chunk_overlap),
            "PIPELINE_VERSION": config.pipeline.pipeline_version,
        }

        lambdas_cfg = config.pipeline.lambdas
        self.functions: dict[str, lambda_.Function] = {}

        for key, fn_cfg in (
            ("router", lambdas_cfg.router),
            ("sebi_parser", lambdas_cfg.sebi_parser),
            ("insurance_parser", lambdas_cfg.insurance_parser),
            ("catalogue_parser", lambdas_cfg.catalogue_parser),
            ("chunker", lambdas_cfg.chunker),
            ("tagger", lambdas_cfg.tagger),
            ("embedder", lambdas_cfg.embedder),
        ):
            function = self._create_lambda_function(
                fn_key=key,
                fn_cfg=fn_cfg,
                role=iam_stack.lambda_execution_role,
                vpc=imported_vpc,
                subnets=private_subnets,
                security_group=lambda_security_group,
                environment=common_env,
            )
            if function is not None:
                self.functions[key] = function

        for key, function in self.functions.items():
            CfnOutput(
                self,
                f"{key.title().replace('_', '')}FunctionArn",
                value=function.function_arn,
                export_name=f"{construct_id}-{key.replace('_', '')}-FunctionArn",
            )

    def _create_lambda_function(
        self,
        *,
        fn_key: str,
        fn_cfg: LambdaFunctionConfig,
        role,
        vpc: ec2.IVpc,
        subnets: list[ec2.ISubnet],
        security_group: ec2.ISecurityGroup,
        environment: dict[str, str],
    ) -> Optional[lambda_.Function]:
        if not fn_cfg.enabled:
            return None

        runtime = self._resolve_runtime(fn_cfg.runtime)

        return lambda_.Function(
            self,
            f"{fn_key.title().replace('_', '')}Function",
            function_name=fn_cfg.function_name,
            runtime=runtime,
            handler=fn_cfg.handler,
            code=lambda_.Code.from_asset(fn_cfg.code_path),
            memory_size=fn_cfg.memory_mb,
            timeout=Duration.seconds(fn_cfg.timeout_seconds),
            role=role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=subnets),
            security_groups=[security_group],
            environment=environment,
        )

    def _resolve_runtime(self, runtime_name: str) -> lambda_.Runtime:
        runtime_map = {
            "python3.9": lambda_.Runtime.PYTHON_3_9,
            "python3.10": lambda_.Runtime.PYTHON_3_10,
            "python3.11": lambda_.Runtime.PYTHON_3_11,
            "python3.12": lambda_.Runtime.PYTHON_3_12,
        }
        if runtime_name not in runtime_map:
            raise ValueError(f"Unsupported Lambda runtime in config: {runtime_name}")
        return runtime_map[runtime_name]
