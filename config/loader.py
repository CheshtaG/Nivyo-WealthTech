from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from config.models import (
    AppConfig,
    AwsConfig,
    BedrockConfig,
    BedrockInterfaceEndpointConfig,
    EmbeddingModelConfig,
    IamConfig,
    IamRolesConfig,
    InputBucketConfig,
    KnowledgeBaseConfig,
    LambdaFunctionConfig,
    SecurityGroupConfig,
    SecurityGroupRuleConfig,
    NatGatewayConfig,
    NetworkConfig,
    NetworkResourceNamesConfig,
    ObservabilityConfig,
    OpenSearchServerlessConfig,
    PipelineConfig,
    PipelineLambdasConfig,
    ProjectConfig,
    S3BucketConfig,
    S3EventNotificationConfig,
    S3GatewayEndpointConfig,
    SecurityGroupsConfig,
    StackToggle,
    StacksConfig,
    StorageConfig,
    VectorStoreFieldConfig,
    VpcEndpointsConfig,
    VpcFlowLogsConfig,
)


def _require(data: dict[str, Any], key: str, path: str) -> Any:
    if key not in data:
        raise ValueError(f"Missing required config key: {path}.{key}")
    return data[key]


def _require_str(data: dict[str, Any], key: str, path: str) -> str:
    value = _require(data, key, path)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Config key {path}.{key} must be a non-empty string")
    return value


def _require_string_value(data: dict[str, Any], key: str, path: str) -> str:
    value = _require(data, key, path)
    if not isinstance(value, str):
        raise ValueError(f"Config key {path}.{key} must be a string")
    return value


def _require_bool(data: dict[str, Any], key: str, path: str) -> bool:
    value = _require(data, key, path)
    if not isinstance(value, bool):
        raise ValueError(f"Config key {path}.{key} must be a boolean")
    return value


def _require_int(data: dict[str, Any], key: str, path: str) -> int:
    value = _require(data, key, path)
    if not isinstance(value, int):
        raise ValueError(f"Config key {path}.{key} must be an integer")
    return value


def _require_str_list(data: dict[str, Any], key: str, path: str) -> tuple[str, ...]:
    value = _require(data, key, path)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Config key {path}.{key} must be a non-empty list of strings")
    return tuple(value)


def _require_named_list_matches_az_count(
    data: dict[str, Any],
    key: str,
    path: str,
    *,
    availability_zones: int,
) -> tuple[str, ...]:
    names = _require_str_list(data, key, path)
    if len(names) != availability_zones:
        raise ValueError(
            f"Config key {path}.{key} must contain exactly "
            f"{availability_zones} name(s) (one per availability zone), got {len(names)}"
        )
    return names


def _load_network_resource_names(
    data: dict[str, Any],
    path: str,
    *,
    availability_zones: int,
) -> NetworkResourceNamesConfig:
    return NetworkResourceNamesConfig(
        internet_gateway=_require_str(data, "internet_gateway", path),
        public_subnets=_require_named_list_matches_az_count(
            data,
            "public_subnets",
            path,
            availability_zones=availability_zones,
        ),
        private_subnets=_require_named_list_matches_az_count(
            data,
            "private_subnets",
            path,
            availability_zones=availability_zones,
        ),
        public_route_table=_require_str(data, "public_route_table", path),
        private_route_tables=_require_named_list_matches_az_count(
            data,
            "private_route_tables",
            path,
            availability_zones=availability_zones,
        ),
        nat_elastic_ip=_require_str(data, "nat_elastic_ip", path),
        nat_gateway=_require_str(data, "nat_gateway", path),
    )


def _load_security_group_rule(data: dict[str, Any], path: str) -> SecurityGroupRuleConfig:
    return SecurityGroupRuleConfig(
        protocol=_require_str(data, "protocol", path),
        from_port=_require_int(data, "from_port", path),
        to_port=_require_int(data, "to_port", path),
        cidr=_require_str(data, "cidr", path),
        description=_require_str(data, "description", path),
    )


def _load_security_group_rules(data: dict[str, Any], key: str, path: str) -> tuple[SecurityGroupRuleConfig, ...]:
    value = _require(data, key, path)
    if not isinstance(value, list):
        raise ValueError(f"Config key {path}.{key} must be a list")
    rules: list[SecurityGroupRuleConfig] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"Config key {path}.{key}[{index}] must be a mapping")
        rules.append(_load_security_group_rule(item, f"{path}.{key}[{index}]"))
    return tuple(rules)


def _load_security_group(data: dict[str, Any], path: str) -> SecurityGroupConfig:
    return SecurityGroupConfig(
        name=_require_str(data, "name", path),
        description=_require_str(data, "description", path),
        ingress_rules=_load_security_group_rules(data, "ingress_rules", path),
        egress_rules=_load_security_group_rules(data, "egress_rules", path),
    )


def _load_stack_toggle(data: dict[str, Any], path: str) -> StackToggle:
    return StackToggle(
        enabled=_require_bool(data, "enabled", path),
        id=_require_str(data, "id", path),
    )


def _load_lambda_function(data: dict[str, Any], path: str) -> LambdaFunctionConfig:
    return LambdaFunctionConfig(
        enabled=_require_bool(data, "enabled", path),
        function_name=_require_str(data, "function_name", path),
        handler=_require_str(data, "handler", path),
        runtime=_require_str(data, "runtime", path),
        memory_mb=_require_int(data, "memory_mb", path),
        timeout_seconds=_require_int(data, "timeout_seconds", path),
        code_path=_require_str(data, "code_path", path),
    )


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config file must contain a YAML mapping at the root")

    aws_raw = _require(raw, "aws", "root")
    project_raw = _require(raw, "project", "root")
    tags_raw = _require(raw, "tags", "root")
    stacks_raw = _require(raw, "stacks", "root")
    network_raw = _require(raw, "network", "root")
    observability_raw = _require(raw, "observability", "root")
    storage_raw = _require(raw, "storage", "root")
    iam_raw = _require(raw, "iam", "root")
    bedrock_raw = _require(raw, "bedrock", "root")
    pipeline_raw = _require(raw, "pipeline", "root")

    if not isinstance(tags_raw, dict) or not tags_raw:
        raise ValueError("root.tags must be a non-empty mapping")
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in tags_raw.items()):
        raise ValueError("root.tags keys and values must be strings")

    nat_raw = _require(network_raw, "nat_gateway", "network")
    endpoints_raw = _require(network_raw, "vpc_endpoints", "network")
    s3_endpoint_raw = _require(endpoints_raw, "s3_gateway", "network.vpc_endpoints")
    bedrock_endpoint_raw = _require(endpoints_raw, "bedrock_interface", "network.vpc_endpoints")
    sg_raw = _require(network_raw, "security_groups", "network")
    lambda_sg_raw = _require(sg_raw, "lambda", "network.security_groups")
    endpoint_sg_raw = _require(sg_raw, "vpc_endpoints", "network.security_groups")

    flow_logs_raw = _require(observability_raw, "vpc_flow_logs", "observability")
    input_bucket_raw = _require(storage_raw, "input_bucket", "storage")
    chunk_bucket_raw = _require(storage_raw, "chunk_store_bucket", "storage")
    event_raw = _require(input_bucket_raw, "event_notifications", "storage.input_bucket")

    iam_roles_raw = _require(iam_raw, "roles", "iam")
    kb_raw = _require(bedrock_raw, "knowledge_base", "bedrock")
    embedding_raw = _require(bedrock_raw, "embedding_model", "bedrock")
    vector_raw = _require(bedrock_raw, "vector_store", "bedrock")
    fields_raw = _require(vector_raw, "fields", "bedrock.vector_store")

    lambdas_raw = _require(pipeline_raw, "lambdas", "pipeline")

    availability_zones = _require_int(network_raw, "availability_zones", "network")
    resource_names_raw = _require(network_raw, "resource_names", "network")

    bedrock_services: tuple[str, ...] = ()
    if _require_bool(bedrock_endpoint_raw, "enabled", "network.vpc_endpoints.bedrock_interface"):
        bedrock_services = _require_str_list(
            bedrock_endpoint_raw,
            "services",
            "network.vpc_endpoints.bedrock_interface",
        )

    return AppConfig(
        aws=AwsConfig(
            account_id=_require_str(aws_raw, "account_id", "aws"),
            region=_require_str(aws_raw, "region", "aws"),
        ),
        project=ProjectConfig(
            name=_require_str(project_raw, "name", "project"),
            environment=_require_str(project_raw, "environment", "project"),
        ),
        tags=dict(tags_raw),
        stacks=StacksConfig(
            vpc=_load_stack_toggle(_require(stacks_raw, "vpc", "stacks"), "stacks.vpc"),
            storage=_load_stack_toggle(_require(stacks_raw, "storage", "stacks"), "stacks.storage"),
            iam=_load_stack_toggle(_require(stacks_raw, "iam", "stacks"), "stacks.iam"),
            bedrock=_load_stack_toggle(_require(stacks_raw, "bedrock", "stacks"), "stacks.bedrock"),
            pipeline=_load_stack_toggle(_require(stacks_raw, "pipeline", "stacks"), "stacks.pipeline"),
            events=_load_stack_toggle(_require(stacks_raw, "events", "stacks"), "stacks.events"),
        ),
        network=NetworkConfig(
            vpc_name=_require_str(network_raw, "vpc_name", "network"),
            vpc_cidr=_require_str(network_raw, "vpc_cidr", "network"),
            enable_dns_support=_require_bool(network_raw, "enable_dns_support", "network"),
            enable_dns_hostnames=_require_bool(network_raw, "enable_dns_hostnames", "network"),
            availability_zones=availability_zones,
            availability_zone_names=_require_str_list(network_raw, "availability_zone_names", "network"),
            public_subnet_cidrs=_require_str_list(network_raw, "public_subnet_cidrs", "network"),
            private_subnet_cidrs=_require_str_list(network_raw, "private_subnet_cidrs", "network"),
            resource_names=_load_network_resource_names(
                resource_names_raw,
                "network.resource_names",
                availability_zones=availability_zones,
            ),
            nat_gateway=NatGatewayConfig(
                enabled=_require_bool(nat_raw, "enabled", "network.nat_gateway"),
            ),
            vpc_endpoints=VpcEndpointsConfig(
                s3_gateway=S3GatewayEndpointConfig(
                    enabled=_require_bool(s3_endpoint_raw, "enabled", "network.vpc_endpoints.s3_gateway"),
                ),
                bedrock_interface=BedrockInterfaceEndpointConfig(
                    enabled=_require_bool(
                        bedrock_endpoint_raw,
                        "enabled",
                        "network.vpc_endpoints.bedrock_interface",
                    ),
                    services=bedrock_services,
                ),
            ),
            security_groups=SecurityGroupsConfig(
                lambda_sg=_load_security_group(lambda_sg_raw, "network.security_groups.lambda"),
                vpc_endpoints_sg=_load_security_group(
                    endpoint_sg_raw,
                    "network.security_groups.vpc_endpoints",
                ),
            ),
        ),
        observability=ObservabilityConfig(
            vpc_flow_logs=VpcFlowLogsConfig(
                enabled=_require_bool(flow_logs_raw, "enabled", "observability.vpc_flow_logs"),
                traffic_type=_require_str(flow_logs_raw, "traffic_type", "observability.vpc_flow_logs"),
                log_group_name=_require_str(flow_logs_raw, "log_group_name", "observability.vpc_flow_logs"),
                retention_days=_require_int(flow_logs_raw, "retention_days", "observability.vpc_flow_logs"),
                removal_policy=_require_str(flow_logs_raw, "removal_policy", "observability.vpc_flow_logs"),
                import_existing_log_group=_require_bool(
                    flow_logs_raw,
                    "import_existing_log_group",
                    "observability.vpc_flow_logs",
                ),
            ),
        ),
        storage=StorageConfig(
            input_bucket=InputBucketConfig(
                name=_require_str(input_bucket_raw, "name", "storage.input_bucket"),
                versioning_enabled=_require_bool(input_bucket_raw, "versioning_enabled", "storage.input_bucket"),
                block_public_access=_require_bool(input_bucket_raw, "block_public_access", "storage.input_bucket"),
                encryption_type=_require_str(input_bucket_raw, "encryption_type", "storage.input_bucket"),
                event_notifications=S3EventNotificationConfig(
                    enabled=_require_bool(event_raw, "enabled", "storage.input_bucket.event_notifications"),
                    prefix=_require_string_value(
                        event_raw,
                        "prefix",
                        "storage.input_bucket.event_notifications",
                    ),
                    suffix=_require_string_value(
                        event_raw,
                        "suffix",
                        "storage.input_bucket.event_notifications",
                    ),
                ),
            ),
            chunk_store_bucket=S3BucketConfig(
                name=_require_str(chunk_bucket_raw, "name", "storage.chunk_store_bucket"),
                versioning_enabled=_require_bool(chunk_bucket_raw, "versioning_enabled", "storage.chunk_store_bucket"),
                block_public_access=_require_bool(chunk_bucket_raw, "block_public_access", "storage.chunk_store_bucket"),
                encryption_type=_require_str(chunk_bucket_raw, "encryption_type", "storage.chunk_store_bucket"),
            ),
        ),
        iam=IamConfig(
            roles=IamRolesConfig(
                lambda_execution_role_name=_require_str(
                    iam_roles_raw,
                    "lambda_execution_role_name",
                    "iam.roles",
                ),
                bedrock_kb_role_name=_require_str(iam_roles_raw, "bedrock_kb_role_name", "iam.roles"),
            ),
        ),
        bedrock=BedrockConfig(
            knowledge_base=KnowledgeBaseConfig(
                name=_require_str(kb_raw, "name", "bedrock.knowledge_base"),
                description=_require_str(kb_raw, "description", "bedrock.knowledge_base"),
            ),
            embedding_model=EmbeddingModelConfig(
                model_id=_require_str(embedding_raw, "model_id", "bedrock.embedding_model"),
                dimensions=_require_int(embedding_raw, "dimensions", "bedrock.embedding_model"),
            ),
            vector_store=OpenSearchServerlessConfig(
                collection_name=_require_str(vector_raw, "collection_name", "bedrock.vector_store"),
                collection_type=_require_str(vector_raw, "collection_type", "bedrock.vector_store"),
                vector_index_name=_require_str(vector_raw, "vector_index_name", "bedrock.vector_store"),
                allow_public_network_access=_require_bool(
                    vector_raw,
                    "allow_public_network_access",
                    "bedrock.vector_store",
                ),
                fields=VectorStoreFieldConfig(
                    vector_field=_require_str(fields_raw, "vector_field", "bedrock.vector_store.fields"),
                    text_field=_require_str(fields_raw, "text_field", "bedrock.vector_store.fields"),
                    metadata_field=_require_str(fields_raw, "metadata_field", "bedrock.vector_store.fields"),
                ),
            ),
        ),
        pipeline=PipelineConfig(
            chunk_size=_require_int(pipeline_raw, "chunk_size", "pipeline"),
            chunk_overlap=_require_int(pipeline_raw, "chunk_overlap", "pipeline"),
            pipeline_version=_require_str(pipeline_raw, "pipeline_version", "pipeline"),
            embedding_model_id=_require_str(pipeline_raw, "embedding_model_id", "pipeline"),
            lambdas=PipelineLambdasConfig(
                router=_load_lambda_function(_require(lambdas_raw, "router", "pipeline.lambdas"), "pipeline.lambdas.router"),
                sebi_parser=_load_lambda_function(
                    _require(lambdas_raw, "sebi_parser", "pipeline.lambdas"),
                    "pipeline.lambdas.sebi_parser",
                ),
                insurance_parser=_load_lambda_function(
                    _require(lambdas_raw, "insurance_parser", "pipeline.lambdas"),
                    "pipeline.lambdas.insurance_parser",
                ),
                catalogue_parser=_load_lambda_function(
                    _require(lambdas_raw, "catalogue_parser", "pipeline.lambdas"),
                    "pipeline.lambdas.catalogue_parser",
                ),
                chunker=_load_lambda_function(_require(lambdas_raw, "chunker", "pipeline.lambdas"), "pipeline.lambdas.chunker"),
                tagger=_load_lambda_function(_require(lambdas_raw, "tagger", "pipeline.lambdas"), "pipeline.lambdas.tagger"),
                embedder=_load_lambda_function(
                    _require(lambdas_raw, "embedder", "pipeline.lambdas"),
                    "pipeline.lambdas.embedder",
                ),
            ),
        ),
    )
