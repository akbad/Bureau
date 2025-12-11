# Cleanup module

**<ins>What it does</ins>**

Handles **automatic, retention-based cleanup for Beehive's memory backends**

- Enforces configurable retention periods across all storage systems
- Provides a recoverable trash system where stale memories are initially moved to

**<ins>Contents</ins>**
- [Purpose](#purpose)
- [Implementation](#implementation)
  - [Cleanup process](#cleanup-process)
- [Handlers](#handlers)
  - [Implementation strategies](#implementation-strategies)
  - [claude-mem (SQLite)](#claude-mem-sqlite)
  - [qdrant (HTTP API)](#qdrant-http-api)
  - [serena (Filesystem)](#serena-filesystem)
  - [memory-mcp (JSONL)](#memory-mcp-jsonl)
- [Configuration](#configuration)
- [CLI commands](#cli-commands)
  - [`sweep-hive` options](#sweep-hive-options)
- [Trash system](#trash-system)
  - [Manifest format](#manifest-format)
- [State management](#state-management)

## Purpose

**Preventing unbounded memory growth** as they accumulate over sessions , while **enabling recovery** before permanent deletion occurs:

1. Export stale items to `.wax/trash/<backend>/`
2. Trashed items are permanently deleted after a grace period *(30 days by default)*

## Implementation

### Cleanup process

`core.run_cleanup()` is the main cleanup orchestrator. When it's called:

1. [Configuration](../../../docs/CONFIGURATION.md) is validated to ensure:
    
    - Required keys exist
    - Values are the correct type
        
        > This includes verifying that the duration strings, as used for the retention period settings, are in the correct format (e.g. `30d`, `3m`).

2. Ensure it's been $\geq 24$ hours since the last cleanup run; if not, exit.

    > To override, use `--force`/`-f`.

3. For each storage backend *(via [its corresponding handler class](handlers/)'s `cleanup()` entrypoint)*:

    1. Compute the staleness cutoff based on the retention period set for the backend (via `get_cutoff()`)

        > If the retention period is `always`, this cutoff will be set to `datetime.min` *(⇒ no items will be older than this)*.

    2. Find stale/expired items (via `get_expired_items(cutoff)`)
    3. Move stale items to trash (via `export_to_trash(items)`) 
       
        - Trash directories are per-storage-backend: `.wax/trash/<backend>`

    4. Delete the stale items from the storage backend's underlying DB (via `delete_items(items)`)

> [!NOTE]
>
> **Handlers follow a plugin-based architecture:**
>
> - The `CleanupHandler` abstract base class defines the `cleanup()` entrypoint used in step 3
> - The concrete subclasses of `CleanupHandler` extend it by implementing the `get_expired_items`, `export_to_trash` and `delete_items` methods above for their specific storage backend

4. Permanently delete items in trash that are older than the configured grace period (via `empty_expired_trash()`)
5. Update `last_cleanup_run` timestamp *(used in step 2)*
