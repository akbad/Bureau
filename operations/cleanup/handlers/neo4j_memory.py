"""Neo4j-based Memory MCP cleanup handler."""

import json
import os
from datetime import datetime, timezone
from typing import Any

from neo4j import GraphDatabase

from .base import CleanupHandler
from ..trash import get_trash_dir, generate_trash_filename, write_manifest
from ...config_loader import get_config, get_trash_grace_period


class Neo4jMemoryHandler(CleanupHandler):
    """Cleanup handler for Neo4j-backed knowledge graph (mcp-neo4j-memory)."""

    name = "neo4j-memory"

    def __init__(self):
        """Initialize Neo4j driver."""
        self._driver = None

    def _get_driver(self):
        """Get or create Neo4j driver."""
        if self._driver is None:
            config = get_config()
            neo4j_cfg = config.get("neo4j", {})
            port_cfg = config.get("port_for", {})

            uri = os.getenv(
                "NEO4J_URI",
                f"bolt://localhost:{port_cfg.get('neo4j_db', 7687)}",
            )
            username = os.getenv(
                "NEO4J_USERNAME", neo4j_cfg.get("auth", {}).get("username", "neo4j")
            )
            password = os.getenv(
                "NEO4J_PASSWORD", neo4j_cfg.get("auth", {}).get("password", "bureau")
            )

            self._driver = GraphDatabase.driver(uri, auth=(username, password))
        return self._driver

    def close(self):
        """Close Neo4j driver."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def get_stale_items(self, cutoff: datetime) -> list[dict[str, Any]]:
        """Find Memory nodes with created_at older than cutoff."""
        driver = self._get_driver()

        # Query for Memory nodes with created_at observation older than cutoff
        query = """
        MATCH (m:Memory)
        WHERE m.created_at IS NOT NULL AND m.created_at < $cutoff
        RETURN m.name AS name,
               m.entityType AS entityType,
               m.created_at AS created_at,
               m.observations AS observations
        ORDER BY m.created_at
        """

        items = []
        try:
            with driver.session() as session:
                result = session.run(query, cutoff=cutoff.isoformat())
                for record in result:
                    items.append(
                        {
                            "name": record["name"],
                            "entityType": record["entityType"],
                            "created_at": record["created_at"],
                            "observations": record["observations"],
                        }
                    )
        except Exception:
            # Connection or query error - return empty list
            pass

        return items

    def export_items_to_trash(self, items: list[dict[str, Any]], retention: str) -> str:
        """Export Memory nodes to JSONL in trash directory."""
        trash_dir = get_trash_dir(self.name)
        filename = generate_trash_filename(len(items), "jsonl")
        trash_path = trash_dir / filename

        with open(trash_path, "w") as f:
            for item in items:
                f.write(json.dumps(item) + "\n")

        write_manifest(
            trash_dir,
            self.name,
            len(items),
            retention,
            get_trash_grace_period(),
            files=[trash_path],
        )

        return str(trash_path)

    def delete_items_from_storage(self, items: list[dict[str, Any]]) -> int:
        """Delete stale Memory nodes and their relationships."""
        if not items:
            return 0

        driver = self._get_driver()
        names = [item["name"] for item in items]

        # Delete nodes and all their relationships
        query = """
        MATCH (m:Memory)
        WHERE m.name IN $names
        DETACH DELETE m
        RETURN count(*) AS deleted
        """

        try:
            with driver.session() as session:
                result = session.run(query, names=names)
                record = result.single()
                return record["deleted"] if record else 0
        except Exception:
            return 0

    def wipe(self, backup: bool = True) -> dict[str, Any]:
        """Completely erase all Memory nodes from Neo4j."""
        driver = self._get_driver()

        # Get all Memory nodes for backup
        query = """
        MATCH (m:Memory)
        RETURN m.name AS name,
               m.entityType AS entityType,
               m.created_at AS created_at,
               m.observations AS observations
        """

        try:
            with driver.session() as session:
                result = session.run(query)
                all_items = [
                    {
                        "name": record["name"],
                        "entityType": record["entityType"],
                        "created_at": record["created_at"],
                        "observations": record["observations"],
                    }
                    for record in result
                ]
        except Exception:
            return {"storage": self.name, "wiped": 0, "error": "failed to connect"}

        if not all_items:
            return {"storage": self.name, "wiped": 0, "message": "no entities found"}

        # Backup if requested
        backup_path = None
        if backup:
            backup_path = self.export_items_to_trash(all_items, "wipe")

        # Delete all Memory nodes
        delete_query = "MATCH (m:Memory) DETACH DELETE m RETURN count(*) AS deleted"

        try:
            with driver.session() as session:
                result = session.run(delete_query)
                record = result.single()
                count = record["deleted"] if record else 0
        except Exception:
            return {"storage": self.name, "wiped": 0, "error": "delete failed"}

        result_dict: dict[str, Any] = {"storage": self.name, "wiped": count}
        if backup_path:
            result_dict["backup_path"] = backup_path
        return result_dict
