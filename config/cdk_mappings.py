from aws_cdk import RemovalPolicy
from aws_cdk import aws_logs as logs


def removal_policy(value: str) -> RemovalPolicy:
    mapping = {
        "RETAIN": RemovalPolicy.RETAIN,
        "DESTROY": RemovalPolicy.DESTROY,
        "SNAPSHOT": RemovalPolicy.SNAPSHOT,
    }
    if value not in mapping:
        raise ValueError(f"Unsupported removal_policy value: {value}")
    return mapping[value]


def log_retention_days(days: int) -> logs.RetentionDays:
    if days <= 1:
        return logs.RetentionDays.ONE_DAY
    if days <= 3:
        return logs.RetentionDays.THREE_DAYS
    if days <= 5:
        return logs.RetentionDays.FIVE_DAYS
    if days <= 7:
        return logs.RetentionDays.ONE_WEEK
    if days <= 14:
        return logs.RetentionDays.TWO_WEEKS
    if days <= 30:
        return logs.RetentionDays.ONE_MONTH
    if days <= 60:
        return logs.RetentionDays.TWO_MONTHS
    if days <= 90:
        return logs.RetentionDays.THREE_MONTHS
    if days <= 120:
        return logs.RetentionDays.FOUR_MONTHS
    if days <= 150:
        return logs.RetentionDays.FIVE_MONTHS
    if days <= 180:
        return logs.RetentionDays.SIX_MONTHS
    if days <= 365:
        return logs.RetentionDays.ONE_YEAR
    if days <= 400:
        return logs.RetentionDays.THIRTEEN_MONTHS
    if days <= 545:
        return logs.RetentionDays.EIGHTEEN_MONTHS
    if days <= 730:
        return logs.RetentionDays.TWO_YEARS
    if days <= 1825:
        return logs.RetentionDays.FIVE_YEARS
    return logs.RetentionDays.TEN_YEARS
