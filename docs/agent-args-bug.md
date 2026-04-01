# Bug Report: Unsafe Agent Argument Expansion in Protocol Setup Script

## Summary
The protocol setup script builds repeated --agent arguments using unquoted array expansion. This breaks argument boundaries when agent names contain spaces (for example, Claude Code and Gemini CLI), causing incorrect argv passed into configure-hooks.py.

## Affected File and Lines
- [protocols/scripts/set-up-protocols.sh](../protocols/scripts/set-up-protocols.sh#L277)
- [protocols/scripts/set-up-protocols.sh](../protocols/scripts/set-up-protocols.sh#L396)

Both call sites currently use this pattern:

    ${AGENTS[*]/#/--agent }

## Severity
High

Reason:
- This can produce malformed CLI arguments during install/update/bare flows.
- Hook configuration and hook removal are core setup operations.
- The bug is data-dependent and appears whenever selected agent names include spaces.

## Environment
- OS: macOS
- Shell: bash (script runtime), zsh (invocation shell)
- Repository: Bureau
- Branch: feat/concierge

## Preconditions
- AGENTS contains at least one value with whitespace, such as:
  - Claude Code
  - Gemini CLI

## Steps to Reproduce
1. Run the setup script in any mode that reaches either configure-hooks.py call path.
2. Ensure AGENTS includes values with spaces.
3. Observe the effective argv construction from the unquoted expansion.

A representative expansion can become tokenized like this:
- --agent Claude Code --agent Gemini CLI

This is interpreted as separate tokens rather than preserving each full agent name as one value.

## Expected Behavior
Each agent name is passed as one atomic value:
- --agent "Claude Code" --agent "Gemini CLI"

Equivalent safe argv semantics should be preserved even for names containing spaces, glob characters, or shell-sensitive content.

## Actual Behavior
The script relies on unquoted ${AGENTS[*]/#/--agent } expansion at two sites, allowing shell word-splitting and potential globbing. This can split one logical agent name into multiple tokens.

## Root Cause Analysis
1. ${AGENTS[*]} joins all array elements into one string using IFS semantics.
2. The resulting string is not quoted at invocation.
3. Shell performs word-splitting after expansion.
4. Agent names containing spaces are split into multiple argv entries.

This is a classic shell quoting boundary error and is flagged by static analysis.

## Static Analysis Evidence
ShellCheck reports:
- SC2048 (use "${array[@]}" instead of ${array[*]} for safe element handling)
- SC2086 (double quote to prevent word splitting and globbing)

Impacted lines are the two call sites listed above.

## Impact Assessment
Functional impact:
- configure-hooks.py may receive unexpected extra positional tokens.
- --agent options may be paired with incomplete values.
- Hook install/remove behavior may fail or partially apply.

Operational impact:
- Setup reliability degrades for common default agent names.
- Failures may look intermittent if only some environments include affected agents.

## Recommended Fix
Construct a dedicated argument array once and reuse it at each call site.

Implementation pattern:

    AGENT_ARGS=()
    for agent in "${AGENTS[@]}"; do
        AGENT_ARGS+=(--agent "$agent")
    done

Then invoke:

    "${AGENT_ARGS[@]}"

This preserves per-element argument boundaries and prevents word-splitting/globbing issues.

## Suggested Patch Locations
- Build AGENT_ARGS immediately after agent discovery near [protocols/scripts/set-up-protocols.sh](../protocols/scripts/set-up-protocols.sh#L57)
- Replace expansion at [protocols/scripts/set-up-protocols.sh](../protocols/scripts/set-up-protocols.sh#L277)
- Replace expansion at [protocols/scripts/set-up-protocols.sh](../protocols/scripts/set-up-protocols.sh#L396)

## Validation Plan
1. Re-run ShellCheck and confirm SC2048/SC2086 are resolved for these locations.
2. Test with AGENTS values that include spaces.
3. Verify both flows:
- bare mode hook removal path
- non-bare mode hook configuration path
4. Confirm configure-hooks.py receives correctly grouped --agent values.

## Regression Test Ideas
- Add a shell-level test fixture that exports AGENTS with spaced names and captures argv seen by a stub configure-hooks.py.
- Assert exact argv sequence and value boundaries.
- Include at least one agent name containing wildcard-like characters to confirm no glob expansion occurs.

## Workaround
No robust workaround at runtime other than avoiding spaced agent names, which is not acceptable for current canonical names.

## Status
Open
