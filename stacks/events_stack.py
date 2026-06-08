from aws_cdk import Stack
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3n
from constructs import Construct

from config.models import AppConfig
from stacks.pipeline_stack import PipelineStack
from stacks.storage_stack import StorageStack


class EventsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: AppConfig,
        storage_stack: StorageStack,
        pipeline_stack: PipelineStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        router_fn = pipeline_stack.functions.get("router")
        event_cfg = config.storage.input_bucket.event_notifications
        if router_fn is None or not event_cfg.enabled:
            return

        notification_filter = None
        if event_cfg.prefix or event_cfg.suffix:
            notification_filter = s3.NotificationKeyFilter(
                prefix=event_cfg.prefix,
                suffix=event_cfg.suffix,
            )

        if notification_filter is not None:
            storage_stack.buckets.input_bucket.add_event_notification(
                s3.EventType.OBJECT_CREATED,
                s3n.LambdaDestination(router_fn),
                notification_filter,
            )
        else:
            storage_stack.buckets.input_bucket.add_event_notification(
                s3.EventType.OBJECT_CREATED,
                s3n.LambdaDestination(router_fn),
            )
