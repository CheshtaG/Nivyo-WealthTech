from dataclasses import dataclass


@dataclass(frozen=True)
class AwsConfig:
    account_id: str
    region: str


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    environment: str


@dataclass(frozen=True)
class StackToggle:
    enabled: bool
    id: str


@dataclass(frozen=True)
class StacksConfig:
    vpc: StackToggle
    storage: StackToggle
    iam: StackToggle
    bedrock: StackToggle
    pipeline: StackToggle
    events: StackToggle


@dataclass(frozen=True)
class NatGatewayConfig:
    enabled: bool


@dataclass(frozen=True)
class S3GatewayEndpointConfig:
    enabled: bool


@dataclass(frozen=True)
class BedrockInterfaceEndpointConfig:
    enabled: bool
    services: tuple[str, ...]


@dataclass(frozen=True)
class VpcEndpointsConfig:
    s3_gateway: S3GatewayEndpointConfig
    bedrock_interface: BedrockInterfaceEndpointConfig


@dataclass(frozen=True)
class SecurityGroupRuleConfig:
    protocol: str
    from_port: int
    to_port: int
    cidr: str
    description: str


@dataclass(frozen=True)
class SecurityGroupConfig:
    name: str
    description: str
    ingress_rules: tuple[SecurityGroupRuleConfig, ...]
    egress_rules: tuple[SecurityGroupRuleConfig, ...]


@dataclass(frozen=True)
class SecurityGroupsConfig:
    lambda_sg: SecurityGroupConfig
    vpc_endpoints_sg: SecurityGroupConfig


@dataclass(frozen=True)
class NetworkResourceNamesConfig:
    internet_gateway: str
    public_subnets: tuple[str, ...]
    private_subnets: tuple[str, ...]
    public_route_table: str
    private_route_tables: tuple[str, ...]
    nat_elastic_ip: str
    nat_gateway: str


@dataclass(frozen=True)
class NetworkConfig:
    vpc_name: str
    vpc_cidr: str
    enable_dns_support: bool
    enable_dns_hostnames: bool
    availability_zones: int
    availability_zone_names: tuple[str, ...]
    public_subnet_cidrs: tuple[str, ...]
    private_subnet_cidrs: tuple[str, ...]
    resource_names: NetworkResourceNamesConfig
    nat_gateway: NatGatewayConfig
    vpc_endpoints: VpcEndpointsConfig
    security_groups: SecurityGroupsConfig


@dataclass(frozen=True)
class VpcFlowLogsConfig:
    enabled: bool
    traffic_type: str
    log_group_name: str
    retention_days: int
    removal_policy: str
    import_existing_log_group: bool


@dataclass(frozen=True)
class ObservabilityConfig:
    vpc_flow_logs: VpcFlowLogsConfig


@dataclass(frozen=True)
class S3BucketConfig:
    name: str
    versioning_enabled: bool
    block_public_access: bool
    encryption_type: str


@dataclass(frozen=True)
class S3EventNotificationConfig:
    enabled: bool
    prefix: str
    suffix: str


@dataclass(frozen=True)
class InputBucketConfig(S3BucketConfig):
    event_notifications: S3EventNotificationConfig


@dataclass(frozen=True)
class StorageConfig:
    input_bucket: InputBucketConfig
    chunk_store_bucket: S3BucketConfig


@dataclass(frozen=True)
class IamRolesConfig:
    lambda_execution_role_name: str
    bedrock_kb_role_name: str


@dataclass(frozen=True)
class IamConfig:
    roles: IamRolesConfig


@dataclass(frozen=True)
class EmbeddingModelConfig:
    model_id: str
    dimensions: int


@dataclass(frozen=True)
class VectorStoreFieldConfig:
    vector_field: str
    text_field: str
    metadata_field: str


@dataclass(frozen=True)
class OpenSearchServerlessConfig:
    collection_name: str
    collection_type: str
    vector_index_name: str
    allow_public_network_access: bool
    fields: VectorStoreFieldConfig


@dataclass(frozen=True)
class KnowledgeBaseConfig:
    name: str
    description: str


@dataclass(frozen=True)
class BedrockConfig:
    knowledge_base: KnowledgeBaseConfig
    embedding_model: EmbeddingModelConfig
    vector_store: OpenSearchServerlessConfig


@dataclass(frozen=True)
class LambdaFunctionConfig:
    enabled: bool
    function_name: str
    handler: str
    runtime: str
    memory_mb: int
    timeout_seconds: int
    code_path: str


@dataclass(frozen=True)
class PipelineLambdasConfig:
    router: LambdaFunctionConfig
    sebi_parser: LambdaFunctionConfig
    insurance_parser: LambdaFunctionConfig
    catalogue_parser: LambdaFunctionConfig
    chunker: LambdaFunctionConfig
    tagger: LambdaFunctionConfig
    embedder: LambdaFunctionConfig


@dataclass(frozen=True)
class PipelineConfig:
    chunk_size: int
    chunk_overlap: int
    pipeline_version: str
    embedding_model_id: str
    lambdas: PipelineLambdasConfig


@dataclass(frozen=True)
class AppConfig:
    aws: AwsConfig
    project: ProjectConfig
    tags: dict[str, str]
    stacks: StacksConfig
    network: NetworkConfig
    observability: ObservabilityConfig
    storage: StorageConfig
    iam: IamConfig
    bedrock: BedrockConfig
    pipeline: PipelineConfig

    def resource_name(self, suffix: str) -> str:
        return f"{self.project.name}-{self.project.environment}-{suffix}"
