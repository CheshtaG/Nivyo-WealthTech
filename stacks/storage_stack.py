from aws_cdk import CfnOutput, Stack
from constructs import Construct

from components.storage_buckets import StorageBuckets
from config.models import AppConfig


class StorageStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: AppConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.buckets = StorageBuckets(self, "Buckets", config=config)

        CfnOutput(
            self,
            "InputBucketName",
            value=self.buckets.input_bucket.bucket_name,
            export_name=f"{construct_id}-InputBucketName",
        )
        CfnOutput(
            self,
            "InputBucketArn",
            value=self.buckets.input_bucket.bucket_arn,
            export_name=f"{construct_id}-InputBucketArn",
        )
        CfnOutput(
            self,
            "ChunkStoreBucketName",
            value=self.buckets.chunk_store_bucket.bucket_name,
            export_name=f"{construct_id}-ChunkStoreBucketName",
        )
        CfnOutput(
            self,
            "ChunkStoreBucketArn",
            value=self.buckets.chunk_store_bucket.bucket_arn,
            export_name=f"{construct_id}-ChunkStoreBucketArn",
        )
