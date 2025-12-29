"""Bureau Graph Extras MCP - blast_radius and cycle detection for Neo4j."""

import asyncio
import json
import os
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "bureau")

server = Server("bureau-graph-extras")
_driver = None


def get_driver():
    """Get or create Neo4j driver singleton."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    return _driver


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="blast_radius",
            description=(
                "Find all entities transitively affected by changing a given entity. "
                "Returns affected entities with their distance from the source. "
                "Use this BEFORE making changes to understand downstream impact."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Name of the source entity to analyze impact for",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["entity"],
            },
        ),
        Tool(
            name="detect_cycles",
            description=(
                "Find circular dependencies in the knowledge graph. "
                "Optionally filter to cycles involving a specific entity. "
                "Useful for debugging dependency issues and finding problematic patterns."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Optional: only find cycles involving this entity",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max cycles to return (default: 10)",
                        "default": 10,
                    },
                },
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    driver = get_driver()

    if name == "blast_radius":
        return await _blast_radius(driver, arguments)
    elif name == "detect_cycles":
        return await _detect_cycles(driver, arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _blast_radius(driver, arguments: dict[str, Any]) -> list[TextContent]:
    """Find all entities affected by changing a given entity."""
    entity = arguments["entity"]
    max_depth = arguments.get("max_depth", 10)

    # Query to find all downstream entities using variable-length path matching
    # Works with mcp-neo4j-memory's Memory node structure
    query = """
    MATCH (source:Memory {name: $entity})
    MATCH path = (source)-[*1..$max_depth]->(affected:Memory)
    WHERE source <> affected
    WITH DISTINCT affected, min(length(path)) AS distance
    RETURN affected.name AS affected_entity,
           affected.entityType AS entity_type,
           distance
    ORDER BY distance, affected_entity
    """

    try:
        with driver.session() as session:
            result = session.run(query, entity=entity, max_depth=max_depth)
            affected = [
                {
                    "entity": r["affected_entity"],
                    "type": r["entity_type"],
                    "distance": r["distance"],
                }
                for r in result
            ]

        if not affected:
            # Check if entity exists
            check_query = "MATCH (m:Memory {name: $entity}) RETURN m.name AS name"
            with driver.session() as session:
                exists = session.run(check_query, entity=entity).single()
                if exists:
                    return [
                        TextContent(
                            type="text",
                            text=f"Entity '{entity}' exists but has no downstream dependencies.",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Entity '{entity}' not found in the knowledge graph.",
                        )
                    ]

        response = {
            "source": entity,
            "affected_count": len(affected),
            "max_depth_searched": max_depth,
            "affected": affected,
        }
        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error querying Neo4j: {str(e)}")]


async def _detect_cycles(driver, arguments: dict[str, Any]) -> list[TextContent]:
    """Find circular dependencies in the knowledge graph."""
    entity = arguments.get("entity")
    limit = arguments.get("limit", 10)

    try:
        if entity:
            # Find cycles involving specific entity
            query = """
            MATCH path = (n:Memory {name: $entity})-[*1..10]->(n)
            RETURN [node IN nodes(path) | node.name] AS cycle_path
            LIMIT $limit
            """
            params = {"entity": entity, "limit": limit}
        else:
            # Find all cycles in the graph
            query = """
            MATCH path = (n:Memory)-[*1..10]->(n)
            WITH [node IN nodes(path) | node.name] AS cycle_path
            RETURN DISTINCT cycle_path
            LIMIT $limit
            """
            params = {"limit": limit}

        with driver.session() as session:
            result = session.run(query, **params)
            cycles = [r["cycle_path"] for r in result]

        if not cycles:
            msg = "No cycles found"
            if entity:
                msg += f" involving '{entity}'"
            return [TextContent(type="text", text=msg)]

        response = {
            "cycle_count": len(cycles),
            "cycles": cycles,
        }
        if entity:
            response["filtered_by"] = entity

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error querying Neo4j: {str(e)}")]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
