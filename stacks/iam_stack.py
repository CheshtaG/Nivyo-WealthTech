from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from constructs import Construct

from config.models import AppConfig


class IamStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: AppConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        region = Stack.of(self).region
        account = Stack.of(self).account

        input_bucket_arn = f"arn:aws:s3:::{config.storage.input_bucket.name}"
        chunk_bucket_arn = f"arn:aws:s3:::{config.storage.chunk_store_bucket.name}"

        self.lambda_execution_role = iam.Role(
            self,
            "LambdaExecutionRole",
            role_name=config.iam.roles.lambda_execution_role_name,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for FinRAG pipeline Lambdas",
        )

        self.lambda_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )
        self.lambda_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess")
        )

        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                ],
                resources=[
                    input_bucket_arn,
                    f"{input_bucket_arn}/*",
                    chunk_bucket_arn,
                    f"{chunk_bucket_arn}/*",
                ],
            )
        )

        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:GetFoundationModel",
                ],
                resources=[
                    f"arn:aws:bedrock:{region}::foundation-model/*",
                    f"arn:aws:bedrock:{region}:{account}:inference-profile/*",
                ],
            )
        )
        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate",
                    "bedrock:GetKnowledgeBase",
                    "bedrock:IngestKnowledgeBaseDocuments",
                ],
                resources=[f"arn:aws:bedrock:{region}:{account}:knowledge-base/*"],
            )
        )

        lambda_function_names = [
            fn.function_name
            for fn in (
                config.pipeline.lambdas.router,
                config.pipeline.lambdas.sebi_parser,
                config.pipeline.lambdas.insurance_parser,
                config.pipeline.lambdas.catalogue_parser,
                config.pipeline.lambdas.chunker,
                config.pipeline.lambdas.tagger,
                config.pipeline.lambdas.embedder,
            )
            if fn.enabled
        ]
        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[
                    f"arn:aws:lambda:{region}:{account}:function:{function_name}"
                    for function_name in lambda_function_names
                ],
            )
        )

        self.bedrock_kb_role = iam.Role(
            self,
            "BedrockKnowledgeBaseRole",
            role_name=config.iam.roles.bedrock_kb_role_name,
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Service role for Bedrock Knowledge Base",
        )
        self.bedrock_kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{region}::foundation-model/{config.bedrock.embedding_model.model_id}",
                ],
            )
        )
        self.bedrock_kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=["aoss:APIAccessAll"],
                resources=[f"arn:aws:aoss:{region}:{account}:collection/*"],
            )
        )
