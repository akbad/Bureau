# Filesystem MCP: Deep Dive

## Overview

Comprehensive file operations with batch capabilities, directory trees, and secure path validation. Use when built-in tools don't provide needed functionality.

## Available Tools

### 1. `read_text_file` / `read_file` - Read File Content

**What it does:** Reads complete file contents as text

**Parameters:**
- `path` (required) - Absolute path to file
- `head` (optional) - First N lines only
- `tail` (optional) - Last N lines only

**Returns:** File content as text

**Best for:** Reading files (same as built-in Read)

**Rate limits:** None

### 2. `read_media_file` - Read Images/Audio

**What it does:** Reads binary media files

**Parameters:**
- `path` (required) - Absolute path to media file

**Returns:** Base64 encoded data + MIME type

**Best for:** Images, audio files

**Rate limits:** None

### 3. `read_multiple_files` - Batch File Reading

**What it does:** Reads multiple files simultaneously

**Parameters:**
- `paths` (required) - Array of file paths

**Returns:** Content from all files with paths as reference

**Best for:** Reading 10+ files (30-60% token savings vs multiple Read calls)

**Rate limits:** None

### 4. `write_file` - Create/Overwrite File

**What it does:** Creates new file or overwrites existing

**Parameters:**
- `path` (required) - Absolute path
- `content` (required) - File content

**Returns:** Confirmation

**Best for:** File creation (same as built-in Write)

**Rate limits:** None

### 5. `edit_file` - Line-Based Edits

**What it does:** Makes line-based replacements in file

**Parameters:**
- `path` (required)
- `edits` (required) - Array of `{oldText, newText}`
- `dryRun` (bool, default false) - Preview with git-style diff

**Returns:** Git-style diff showing changes

**Best for:** Multiple edits in one operation

**Rate limits:** None

### 6. `create_directory` - Create Directories

**What it does:** Creates directory or nested directories

**Parameters:**
- `path` (required) - Directory path

**Returns:** Confirmation

**Best for:** Directory setup, ensuring paths exist

**Rate limits:** None

### 7. `list_directory` - List Directory Contents

**What it does:** Lists files and directories

**Parameters:**
- `path` (required) - Directory to list

**Returns:** Contents with [FILE] and [DIR] prefixes

**Best for:** Directory exploration

**Rate limits:** None

### 8. `list_directory_with_sizes` - List with Sizes

**What it does:** Lists contents with file sizes

**Parameters:**
- `path` (required)
- `sortBy` (default "name") - "name" | "size"

**Returns:** Contents with sizes, sorted

**Best for:** Understanding disk usage, finding large files

**Rate limits:** None

### 9. `directory_tree` - Recursive Tree View

**What it does:** Returns JSON tree structure

**Parameters:**
- `path` (required) - Root directory

**Returns:** Recursive JSON tree (files: no children, directories: children array)

**Best for:** Understanding project structure programmatically

**Rate limits:** None

### 10. `move_file` - Move/Rename

**What it does:** Moves or renames files/directories

**Parameters:**
- `source` (required)
- `destination` (required)

**Returns:** Confirmation

**Best for:** File organization, renaming

**Rate limits:** None

### 11. `search_files` - Recursive Search

**What it does:** Recursively searches for files matching pattern

**Parameters:**
- `path` (required) - Starting directory
- `pattern` (required) - Search pattern (case-insensitive, partial)
- `excludePatterns` (default []) - Patterns to exclude

**Returns:** Full paths to matching items

**Best for:** Finding files when location unknown

**Rate limits:** None

### 12. `get_file_info` - File Metadata

**What it does:** Returns detailed file/directory metadata

**Parameters:**
- `path` (required)

**Returns:** Size, creation time, modified time, permissions, type

**Best for:** Understanding file characteristics without reading content

**Rate limits:** None

### 13. `list_allowed_directories` - Show Allowed Paths

**What it does:** Returns directories this server can access

**Parameters:** None

**Returns:** List of allowed root directories

**Best for:** Understanding access boundaries

**Rate limits:** None

## Tradeoffs

### Advantages
✅ **Batch operations** (read_multiple_files: 30-60% token savings)
✅ **Directory trees** (JSON structure)
✅ **Secure path validation** (allowlist enforced)
✅ **Metadata operations** (sizes, permissions, info)
✅ **Recursive search** (find files anywhere)

### Disadvantages
❌ **Overhead for 1-5 files** (built-ins are sufficient)
❌ **No glob patterns** (use Glob tool for that)
❌ **Absolute paths required** (no relative paths)

## Common Pitfalls: When NOT to Use

### ❌ Reading 1-5 Files
**Problem:** Filesystem MCP adds overhead for small operations
**Alternative:** Built-in Read tool

**Example:**
```
Bad:  read_text_file for single file
Good: Read tool (built-in, optimized)
```

### ❌ Writing Single File
**Problem:** Built-in Write already handles this
**Alternative:** Built-in Write tool

**Example:**
```
Bad:  write_file for single file creation
Good: Write tool (built-in)
```

### ❌ Editing with Built-in Edit Available
**Problem:** Built-in Edit handles single-file edits
**Alternative:** Built-in Edit tool

**Example:**
```
Bad:  edit_file for simple replacement
Good: Edit tool (built-in, string-based)
```

### ❌ Glob Pattern Matching
**Problem:** Filesystem search uses simple patterns, not globs
**Alternative:** Glob tool

**Example:**
```
Bad:  search_files("*.tsx")
Good: Glob tool ("**/*.tsx")
```

### ❌ Content Search
**Problem:** Filesystem MCP searches filenames, not content
**Alternative:** Grep tool

**Example:**
```
Bad:  search_files for code patterns
Good: Grep (searches file content)
```

## When Filesystem MCP IS the Right Choice

✅ **Batch reading 10+ files** (significant token savings)
✅ **Directory trees** needed (JSON structure)
✅ **Recursive file search** by name
✅ **File metadata** without reading content
✅ **Directory size analysis**

**Decision rule:** "Do I need batch operations or directory analysis?"

## Usage Patterns

**Batch file reading (10+ files):**
```
read_multiple_files([
  "/path/to/file1.js",
  "/path/to/file2.js",
  "/path/to/file3.js",
  ...
])
→ 30-60% token savings vs multiple Read calls
```

**Directory tree analysis:**
```
directory_tree("/path/to/project")
→ JSON structure showing entire project hierarchy
```

**Find files by name:**
```
search_files(
  path: "/path/to/project",
  pattern: "config",
  excludePatterns: ["node_modules", ".git"]
)
→ All files with "config" in name
```

**Get directory sizes:**
```
list_directory_with_sizes(
  path: "/path/to/dir",
  sortBy: "size"
)
→ Files sorted by size
```

**File metadata:**
```
get_file_info("/path/to/file.js")
→ {size, created, modified, permissions, type}
```

**Multiple edits:**
```
edit_file(
  path: "/path/to/file.js",
  edits: [
    {oldText: "const foo = 1", newText: "const foo = 2"},
    {oldText: "bar()", newText: "baz()"}
  ]
)
→ Git-style diff of changes
```

## When to Use Built-in Tools Instead

**Use built-in tools for:**
- **Read**: 1-5 files, standard reading
- **Write**: Single file creation/overwrite
- **Edit**: Single file, simple replacements
- **Glob**: Pattern matching (`**/*.tsx`)
- **Grep**: Content search in files

**Use Filesystem MCP for:**
- Batch operations (10+ files)
- Directory analysis (trees, sizes)
- File search by name (recursive)
- Metadata operations

## Best Practices

**Batch reading threshold:**
- 1-5 files → Use built-in Read
- 6-9 files → Either works
- 10+ files → Use read_multiple_files (significant savings)

**Directory exploration:**
- Quick look → list_directory
- Size analysis → list_directory_with_sizes
- Full structure → directory_tree (JSON)

**File search:**
- By name → search_files
- By pattern → Glob
- By content → Grep

**Security:**
- Only works within allowed directories
- Use list_allowed_directories to check boundaries
- Absolute paths required

## Alternatives Summary

| Task | Instead of Filesystem MCP | Use This |
|------|--------------------------|----------|
| Read 1-5 files | read_text_file | Read (built-in) |
| Write single file | write_file | Write (built-in) |
| Edit single file | edit_file | Edit (built-in) |
| Glob patterns | search_files | Glob (built-in) |
| Content search | search_files | Grep (built-in) |

## Quick Reference

**Rate limits:** None (local)
**Best for:** Batch operations (10+ files), directory analysis
**Avoid for:** 1-5 files (use built-ins), glob patterns, content search

**Batch reading threshold:** 10+ files → 30-60% token savings

**Tools available:** 13 total
**Security:** Allowlist-based path validation
**Paths:** Absolute paths required

**Links:**
- [Full decision guide](../../../mcps/tools-decision-guide.md)
