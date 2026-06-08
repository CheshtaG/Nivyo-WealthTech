from aws_cdk import aws_s3 as s3
from constructs import Construct

from config.models import AppConfig, S3BucketConfig


def _bucket_encryption(encryption_type: str) -> s3.BucketEncryption:
    if encryption_type == "SSE_S3":
        return s3.BucketEncryption.S3_MANAGED
    if encryption_type == "SSE_KMS":
        return s3.BucketEncryption.KMS_MANAGED
    raise ValueError(f"Unsupported S3 encryption_type: {encryption_type}")


class StorageBuckets(Construct):
    def __init__(self, scope: Construct, construct_id: str, *, config: AppConfig) -> None:
        super().__init__(scope, construct_id)

        self.input_bucket = self._create_bucket(
            self,
            "InputBucket",
            bucket_config=config.storage.input_bucket,
        )
        self.chunk_store_bucket = self._create_bucket(
            self,
            "ChunkStoreBucket",
            bucket_config=config.storage.chunk_store_bucket,
        )

    def _create_bucket(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bucket_config: S3BucketConfig,
    ) -> s3.Bucket:
        bucket = s3.Bucket(
            scope,
            construct_id,
            bucket_name=bucket_config.name,
            versioned=bucket_config.versioning_enabled,
            encryption=_bucket_encryption(bucket_config.encryption_type),
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
            if bucket_config.block_public_access
            else s3.BlockPublicAccess.BLOCK_ACLS,
        )
        return bucket
