import enum


class SourceType(str, enum.Enum):
    pst = "pst"
    imap = "imap"
    mbox = "mbox"
    eml = "eml"


class ThreadKind(str, enum.Enum):
    thread = "thread"
    topic = "topic"


class AIRunKind(str, enum.Enum):
    embedding = "embedding"
    summarize = "summarize"
    classify = "classify"
    extract = "extract"


class AIRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class JobStatus(str, enum.Enum):
    pending = "pending"
    started = "started"
    success = "success"
    failure = "failure"
    retry = "retry"
    revoked = "revoked"
