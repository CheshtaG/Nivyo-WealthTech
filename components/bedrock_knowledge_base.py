import json

from aws_cdk import Stack
from aws_cdk import aws_bedrock as bedrock
from aws_cdk import aws_iam as iam
from aws_cdk import aws_opensearchserverless as oss
from constructs import Construct

from config.models import AppConfig


class BedrockKnowledgeBase(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: AppConfig,
        kb_role: iam.Role,
    ) -> None:
        super().__init__(scope, construct_id)

        stack = Stack.of(self)
        region = stack.region
        account = stack.account

        vector_cfg = config.bedrock.vector_store
        collection_name = vector_cfg.collection_name
        collection_arn = (
            f"arn:aws:aoss:{region}:{account}:collection/{collection_name}"
        )

        encryption_policy = oss.CfnSecurityPolicy(
            self,
            "OpenSearchEncryptionPolicy",
            name=f"{collection_name}-enc",
            type="encryption",
            policy=json.dumps(
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{collection_name}"],
                        }
                    ],
                    "AWSOwnedKey": True,
                }
            ),
        )

        network_policy = oss.CfnSecurityPolicy(
            self,
            "OpenSearchNetworkPolicy",
            name=f"{collection_name}-net",
            type="network",
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "ResourceType": "collection",
                                "Resource": [f"collection/{collection_name}"],
                            },
                            {
                                "ResourceType": "dashboard",
                                "Resource": [f"collection/{collection_name}"],
                            },
                        ],
                        "AllowFromPublic": vector_cfg.allow_public_network_access,
                    }
                ]
            ),
        )

        data_access_policy = oss.CfnAccessPolicy(
            self,
            "OpenSearchDataAccessPolicy",
            name=f"{collection_name}-data",
            type="data",
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "ResourceType": "collection",
                                "Resource": [f"collection/{collection_name}"],
                                "Permission": [
                                    "aoss:CreateCollectionItems",
                                    "aoss:DeleteCollectionItems",
                                    "aoss:UpdateCollectionItems",
                                    "aoss:DescribeCollectionItems",
                                ],
                            },
                            {
                                "ResourceType": "index",
                                "Resource": [f"index/{collection_name}/*"],
                                "Permission": [
                                    "aoss:CreateIndex",
                                    "aoss:DeleteIndex",
                                    "aoss:UpdateIndex",
                                    "aoss:DescribeIndex",
                                    "aoss:ReadDocument",
                                    "aoss:WriteDocument",
                                ],
                            },
                        ],
                        "Principal": [kb_role.role_arn, f"arn:aws:iam::{account}:root"],
                    }
                ]
            ),
        )

        collection = oss.CfnCollection(
            self,
            "OpenSearchCollection",
            name=collection_name,
            type=vector_cfg.collection_type,
            description=f"Vector collection for {config.bedrock.knowledge_base.name}",
        )
        collection.add_dependency(encryption_policy)
        collection.add_dependency(network_policy)
        collection.add_dependency(data_access_policy)

        self.knowledge_base = bedrock.CfnKnowledgeBase(
            self,
            "KnowledgeBase",
            name=config.bedrock.knowledge_base.name,
            description=config.bedrock.knowledge_base.description,
            role_arn=kb_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=(
                        f"arn:aws:bedrock:{region}::foundation-model/"
                        f"{config.bedrock.embedding_model.model_id}"
                    ),
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                    collection_arn=collection.attr_arn,
                    vector_index_name=vector_cfg.vector_index_name,
                    field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                        vector_field=vector_cfg.fields.vector_field,
                        text_field=vector_cfg.fields.text_field,
                        metadata_field=vector_cfg.fields.metadata_field,
                    ),
                ),
            ),
        )
        self.knowledge_base.add_dependency(collection)

        self.collection = collection
