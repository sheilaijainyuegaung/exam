import enum


class TaskStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"


class RuleSecondLevelMode(str, enum.Enum):
    auto = "auto"
    restart = "restart"
    continuous = "continuous"


class DetectedSecondLevelMode(str, enum.Enum):
    restart = "restart"
    continuous = "continuous"
    unknown = "unknown"

