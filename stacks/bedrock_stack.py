from aws_cdk import CfnOutput, Stack
from constructs import Construct

from components.bedrock_knowledge_base import BedrockKnowledgeBase
from config.models import AppConfig
from stacks.iam_stack import IamStack


class BedrockStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: AppConfig,
        iam_stack: IamStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.knowledge_base_resources = BedrockKnowledgeBase(
            self,
            "BedrockKnowledgeBase",
            config=config,
            kb_role=iam_stack.bedrock_kb_role,
        )

        CfnOutput(
            self,
            "KnowledgeBaseId",
            value=self.knowledge_base_resources.knowledge_base.attr_knowledge_base_id,
            export_name=f"{construct_id}-KnowledgeBaseId",
        )
        CfnOutput(
            self,
            "OpenSearchCollectionArn",
            value=self.knowledge_base_resources.collection.attr_arn,
            export_name=f"{construct_id}-OpenSearchCollectionArn",
        )
