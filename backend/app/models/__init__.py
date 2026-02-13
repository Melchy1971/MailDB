# Import every model so that:
#  1. Alembic autogenerate can discover all tables via Base.metadata
#  2. SQLAlchemy relationship back-references resolve at startup

from app.models.mailbox_source import MailboxSource  # noqa: F401
from app.models.folder import Folder  # noqa: F401
from app.models.ai_run import AIRun  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.thread_topic import ThreadOrTopic, TopicEmailMap  # noqa: F401
from app.models.email import Email  # noqa: F401
from app.models.knowledge_article import KnowledgeArticle  # noqa: F401
from app.models.embedding import EmailEmbedding, KnowledgeEmbedding  # noqa: F401
from app.models.app_config import AppConfig  # noqa: F401

__all__ = [
    "MailboxSource",
    "Folder",
    "AIRun",
    "Job",
    "ThreadOrTopic",
    "TopicEmailMap",
    "Email",
    "KnowledgeArticle",
    "EmailEmbedding",
    "KnowledgeEmbedding",
    "AppConfig",
]
