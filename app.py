#!/usr/bin/env python3
from pathlib import Path

import aws_cdk as cdk

from config.loader import load_config
from stacks.bedrock_stack import BedrockStack
from stacks.iam_stack import IamStack
from stacks.events_stack import EventsStack
from stacks.pipeline_stack import PipelineStack
from stacks.storage_stack import StorageStack
from stacks.vpc_stack import VpcStack


def _required_context(app: cdk.App, key: str) -> str:
    value = app.node.try_get_context(key)
    if value in (None, ""):
        raise ValueError(f"Missing required CDK context key: '{key}'")
    return str(value)


app = cdk.App()
config_file = _required_context(app, "config_file")
config_path = Path(config_file)
if not config_path.is_absolute():
    config_path = Path(__file__).resolve().parent / config_path

config = load_config(config_path)

env = cdk.Environment(account=config.aws.account_id, region=config.aws.region)

for key, value in config.tags.items():
    cdk.Tags.of(app).add(key, value)

vpc_stack = None
storage_stack = None
iam_stack = None
bedrock_stack = None
pipeline_stack = None

if config.stacks.vpc.enabled:
    vpc_stack = VpcStack(app, config.stacks.vpc.id, config=config, env=env)

if config.stacks.storage.enabled:
    storage_stack = StorageStack(app, config.stacks.storage.id, config=config, env=env)

if config.stacks.iam.enabled:
    iam_stack = IamStack(app, config.stacks.iam.id, config=config, env=env)

if config.stacks.bedrock.enabled:
    if iam_stack is None:
        raise ValueError("bedrock stack requires iam stack to be enabled and created first")
    bedrock_stack = BedrockStack(
        app,
        config.stacks.bedrock.id,
        config=config,
        iam_stack=iam_stack,
        env=env,
    )

if config.stacks.pipeline.enabled:
    if vpc_stack is None or iam_stack is None or bedrock_stack is None:
        raise ValueError("pipeline stack requires vpc, iam, and bedrock stacks to be enabled")
    pipeline_stack = PipelineStack(
        app,
        config.stacks.pipeline.id,
        config=config,
        vpc_stack=vpc_stack,
        iam_stack=iam_stack,
        bedrock_stack=bedrock_stack,
        env=env,
    )

if config.stacks.events.enabled:
    if storage_stack is None or pipeline_stack is None:
        raise ValueError("events stack requires storage and pipeline stacks to be enabled")
    EventsStack(
        app,
        config.stacks.events.id,
        config=config,
        storage_stack=storage_stack,
        pipeline_stack=pipeline_stack,
        env=env,
    )

app.synth()
