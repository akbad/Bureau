"""Cleanup handlers specific to each memory backend."""
from .base import CleanupHandler
from .qdrant import QdrantHandler
from .claude_mem import ClaudeMemHandler
from .serena import SerenaHandler
from .neo4j_memory import Neo4jMemoryHandler


# register memory backends' handler classes
HANDLERS = (
    ClaudeMemHandler,
    SerenaHandler,
    QdrantHandler,
    Neo4jMemoryHandler,
)


__all__ = [
    "CleanupHandler",
    "QdrantHandler",
    "ClaudeMemHandler",
    "SerenaHandler",
    "Neo4jMemoryHandler",
    "HANDLERS",
]
