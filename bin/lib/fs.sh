#!/usr/bin/env bash
#
# Filesystem library: safe file mutation helpers for all Bureau scripts.
#
# Usage:
#   source "$REPO_ROOT/bin/lib/fs.sh"
#
# Available functions:
#   _sed_inplace "<sed-script>" "<file>"  - Portable, atomic in-place sed
#
# All functions are safe to source under `set -euo pipefail`.
#
# The BSD-vs-GNU rules this library exists to enforce — and the defects that
# earned each of them — are recorded in docs/ENGINEERING.md, "Shell
# portability". Read that before adding a helper here.

# Return the directory component of a path, without spawning `dirname`.
#
# Pure parameter expansion, so a path beginning with `-` can never be parsed as
# an option — the failure that `dirname` itself exhibits. Callers pass paths
# already anchored by `_sed_inplace`, but this stays correct for a bare
# filename ("." ) and for a root-level path ("/").
_dirname_of() {
    local path=${1:-}
    case "$path" in
        */*) path=${path%/*}; printf '%s\n' "${path:-/}" ;;
        *)   printf '%s\n' "." ;;
    esac
}

# Apply a sed script to a file in place, portably and atomically.
#
# Replaces `sed -i`, which cannot be written once for both platforms: BSD/macOS
# requires a backup suffix argument (`sed -i '' <script> <file>`) while GNU
# treats that empty string as a filename and exits 2. Bureau had the BSD
# spelling, so the command was broken outright on Linux.
#
# The temp file is created *in the target's own directory* so the final `mv` is
# a rename within one filesystem — atomic, and never a copy that could be seen
# half-written. A reader either sees the old file or the new one.
#
# Beyond portability, this is safer than `sed -i` in three ways:
#
#   1. A failing sed script leaves the original untouched. `sed -i` can leave a
#      truncated or partially-rewritten file behind.
#   2. Permissions are preserved. `mv`-ing a fresh temp over the target would
#      install the temp's umask-derived mode, quietly widening a 0600 file.
#   3. Symlinks are followed, not replaced. Both seds swap the link for a
#      regular file and silently detach it, which matters here because Bureau
#      deploys symlinked skills and protocol files.
#
# Args:
#   $1 - sed script (e.g. "s|{{PLACEHOLDER}}|value|g")
#   $2 - path to the file to edit
#
# Returns 0 on success; non-zero with a message on stderr otherwise.
_sed_inplace() {
    local script=${1:-}
    local file=${2:-}

    if [[ -z "$script" || -z "$file" ]]; then
        echo "_sed_inplace: usage: _sed_inplace <sed-script> <file>" >&2
        return 2
    fi

    # Anchor a relative path with "./" once, up front. Every external command
    # below (readlink, cp, mv) parses its arguments, so a path like "-weird.md"
    # would be read as options by any of them. This one normalization kills the
    # whole class, which is why no command below needs a `--` guard — and not
    # needing one is the point, since BSD support for `--` cannot be verified
    # from a Linux container.
    [[ "$file" != /* ]] && file="./$file"

    # Follow symlinks before doing anything else: every path below (mode
    # preservation, the same-directory temp, the rename) must act on the real
    # file, or we replace the link instead of editing what it points at.
    #
    # The hop limit is load-bearing, not defensive garnish: two links pointing
    # at each other make `while [[ -L ]]` spin forever, and a setup script that
    # hangs is worse than one that fails. 40 matches the usual kernel ELOOP
    # ceiling, so any chain the OS would itself follow still resolves here.
    local resolved hops=0
    while [[ -L "$file" ]]; do
        if (( ++hops > 40 )); then
            echo "_sed_inplace: too many symlink hops (circular?): $file" >&2
            return 1
        fi
        # `readlink -f` is GNU-only; this loop is the portable equivalent.
        resolved=$(readlink "$file") || break
        # a relative link resolves against its own directory, not $PWD
        [[ "$resolved" != /* ]] && resolved="$(_dirname_of "$file")/$resolved"
        file=$resolved
    done

    if [[ ! -f "$file" ]]; then
        echo "_sed_inplace: not a regular file: $file" >&2
        return 1
    fi
    if [[ ! -w "$file" ]]; then
        echo "_sed_inplace: file is not writable: $file" >&2
        return 1
    fi

    local dir base tmp
    dir=$(_dirname_of "$file")
    base=${file##*/}

    # Same directory => the mv below is a rename, not a cross-device copy.
    # A dotfile prefix keeps a crashed run's leftovers out of glob expansions.
    tmp=$(mktemp "$dir/.$base.XXXXXX") || {
        echo "_sed_inplace: could not create a temp file in $dir" >&2
        return 1
    }

    # `cp -p` seeds the temp with the original's mode and timestamps; the
    # redirection then truncates and rewrites its *contents* without recreating
    # the inode, so the mode survives. This is the portable equivalent of
    # `chmod --reference`, which is GNU-only. No `--` needed: see the path
    # normalization above.
    if ! cp -p "$file" "$tmp"; then
        rm -f "$tmp"
        echo "_sed_inplace: could not stage a copy of $file" >&2
        return 1
    fi

    # No `trap` here on purpose: this is a sourced library, and installing a
    # global EXIT trap would silently replace whatever the calling script had.
    # Each failure path cleans up its own temp instead.
    #
    # The input arrives by redirection rather than as an argument, and the
    # script goes behind `-e`, so neither can ever be parsed as an option —
    # a path beginning with `-` is handled by the shell, not by sed's getopt.
    # This also sidesteps `--`, whose support in BSD sed cannot be verified
    # from a Linux container. Both seds have always accepted `-e`.
    #
    # sed's own stderr is deliberately not suppressed: it names the actual
    # fault ("unterminated `s' command"), which our line below cannot.
    if ! sed -e "$script" < "$file" > "$tmp"; then
        rm -f "$tmp"
        echo "_sed_inplace: sed failed on $file (script: $script)" >&2
        return 1
    fi

    if ! mv -f "$tmp" "$file"; then
        rm -f "$tmp"
        echo "_sed_inplace: could not replace $file" >&2
        return 1
    fi
}
