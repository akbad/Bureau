# Output styles: open issues and review findings

**Date**: 2026-04-01  
**Status**: Open issues after implementation review  
**Scope**: Record the review findings, their practical impact, the code paths involved, and the most appropriate follow-up work for the `output_style` feature.

## Context

The `output_style` feature is now implemented at the core plumbing level:

- Bureau exposes a top-level `output_style` config key.
- Bureau compiles ordered style sources into `~/.config/bureau/protocols/output-style.md`.
- Claude Code receives a native Bureau-managed output style wrapper.
- Codex and Gemini load the compiled style at session start.
- OpenCode receives the compiled style through generated `instructions`.

The review summarized below focused on correctness, regressions, and integration gaps in the current implementation state.

## Summary

The review found **three concrete issues**:

1. **High severity**: `--bare` does not fully disable Bureau-managed context injection.
2. **Medium severity**: `output_style` source paths containing spaces are parsed incorrectly.
3. **Low severity**: Claude bare-mode cleanup can create an empty `~/.claude/settings.json` even when none existed before.

It also identified two broader residual risks:

- Bare-mode behavior has not yet been validated through a real end-to-end smoke test.
- The current protocol deployment tests still cover some behavior through handcrafted shell snippets instead of the full real setup flow.

## Findings

### 1. High: `--bare` still leaves Bureau startup context in place

#### What is wrong

The current bare-mode flow removes the deployed protocols directory and per-prompt hooks, but it does **not** stop the later parts of the setup script from regenerating and re-symlinking Bureau-managed startup context files.

As a result, `--bare` can still leave supported CLIs pointed at Bureau-managed startup context, including the new output-style behavior.

#### Why this matters

This is a direct semantic mismatch with what bare mode is supposed to mean.

- The intended contract is: Bureau should remove its protocol files and stop injecting its context.
- The current behavior appears to be: Bureau removes some runtime artifacts, but then recreates agent-facing startup context later in the same script.

That means a user who explicitly requests bare mode may still get Bureau-controlled behavior in Codex, Gemini, or Claude.

#### Relevant code paths

- [protocols/scripts/set-up-protocols.sh](/Users/danielakbarzadeh/code/bureau-concierge/protocols/scripts/set-up-protocols.sh)

The review highlighted the following phases in the same script:

- bare-mode removal earlier in the script
- unconditional generation and symlinking later in the script

The reviewer specifically called out later generation/symlink flow around these lines in the current file:

- [set-up-protocols.sh](/Users/danielakbarzadeh/code/bureau-concierge/protocols/scripts/set-up-protocols.sh)

#### Practical impact

- Codex and Gemini may still load generated `AGENTS.md`.
- Claude may still load generated `CLAUDE.md`.
- The new `output-style.md` semantics may still effectively participate in startup context even though the user asked for bare mode.

#### Recommended fix

Make bare mode a true short-circuit for Bureau-managed context generation and symlinking.

- In `set-up-protocols.sh`, once bare-mode cleanup completes, do **not** continue into generated `AGENTS.md` / `CLAUDE.md` creation or symlink wiring.
- Treat bare mode as “remove and stop,” not “remove then regenerate.”

#### Missing verification

There is currently no explicit bare-mode integration test proving that Bureau startup context is absent after the full setup flow.

- The reviewer noted that [tools/scripts/tests/test_open_bureau.py](/Users/danielakbarzadeh/code/bureau-concierge/tools/scripts/tests/test_open_bureau.py) only checks ordering, not the final bare-mode outcome.

### 2. Medium: `output_style` paths with spaces will be split incorrectly

#### What is wrong

The config pipeline currently formats list values for shell consumption as a space-separated string, and the shell setup code then splits that string with normal word-splitting semantics.

This breaks any configured output-style source path that contains spaces.

#### Why this matters

This is a real configuration bug, not just a theoretical edge case.

Paths with spaces are common on macOS, especially under locations such as:

- `~/Library/Mobile Documents/...`
- synced cloud-storage directories
- user-created folders with natural-language names

A path like:

```yaml
output_style:
  - "~/Library/Mobile Documents/style.md"
```

would be split into multiple invalid path fragments before compilation.

#### Relevant code paths

- [operations/config_cli.py](/Users/danielakbarzadeh/code/bureau-concierge/operations/config_cli.py)

    - List values are formatted as a single space-separated string.

- [protocols/scripts/set-up-protocols.sh](/Users/danielakbarzadeh/code/bureau-concierge/protocols/scripts/set-up-protocols.sh)

    - The script reads the value back with `read -ra`, which assumes spaces are separators rather than part of a path.

#### Practical impact

- Valid `output_style` configurations can fail unexpectedly.
- The failure mode is confusing because the user has supplied a syntactically valid config, but setup will behave as though the file paths are wrong.

#### Recommended fix

Stop using space-separated shell transport for path lists.

Safer options include:

1. Emit JSON from `operations.config_cli` for list-valued keys and parse it explicitly in shell or Python.
2. Move `output_style` resolution entirely into Python so ordered paths are handled structurally rather than through shell word-splitting.
3. Use NUL-delimited or newline-delimited transport rather than plain spaces if shell mediation must remain.

The cleanest fix is probably to keep path-list resolution in Python rather than pushing list semantics through shell formatting.

#### Missing verification

The current tests only cover no-space paths.

- The reviewer specifically called out [operations/tests/test_config_loader.py](/Users/danielakbarzadeh/code/bureau-concierge/operations/tests/test_config_loader.py) as only covering simple paths.

A regression test should be added for at least one path containing spaces.

### 3. Low: Claude bare-mode cleanup can create an empty settings file

#### What is wrong

The Claude cleanup helper loads a default empty settings object and always writes it back, even if the user never had a `~/.claude/settings.json` file in the first place.

In other words, removing Bureau-managed Claude style state can create a new empty Claude settings file as a side effect.

#### Why this matters

This is low severity, but it is still behavior drift:

- A “remove Bureau state” operation should ideally leave no new user-facing config files behind.
- Creating an empty settings file is not catastrophic, but it is surprising and unnecessary.

#### Relevant code paths

- [protocols/scripts/configure-output-style.py](/Users/danielakbarzadeh/code/bureau-concierge/protocols/scripts/configure-output-style.py)

    - The cleanup path loads `{}` as default and saves it back unconditionally.

- [protocols/scripts/set-up-protocols.sh](/Users/danielakbarzadeh/code/bureau-concierge/protocols/scripts/set-up-protocols.sh)

    - Bare mode calls Claude output-style cleanup unconditionally.

#### Practical impact

- Users who never had Claude settings can end up with a new empty `~/.claude/settings.json`.

#### Recommended fix

Only save Claude settings back if one of the following is true:

- the settings file already existed, or
- the cleanup operation actually removed Bureau-owned state from a non-empty in-memory settings object.

If the file did not exist and there is nothing meaningful to persist, do not create it.

#### Missing verification

The current cleanup tests only cover cases where `settings.json` already exists.

- Add a test for the “no settings file exists” cleanup path.

## Residual risks

### 1. Bare-mode behavior has not been smoke-tested end to end

The highest-severity finding is strongly supported by the code flow, but it has not yet been validated through a full runtime smoke test.

That means the next best validation step is operational, not just unit-level:

1. Run `bin/open-bureau --bare`
2. Inspect the generated/symlinked CLI context state
3. Confirm Claude, Codex, and Gemini are no longer pointed at Bureau-managed startup context

### 2. Protocol deployment integration coverage is still lighter than ideal

The current protocol tests still rely in part on handcrafted shell snippets rather than fully exercising the real setup path.

This matters because `output_style` now spans:

- config loading
- shell orchestration
- runtime file compilation
- Claude-native wrapper installation
- bare-mode cleanup

The more that behavior is verified through the actual scripts and entrypoints, the less likely subtle orchestration regressions will survive.

## Recommended follow-up work

### Must-fix

1. Fix bare mode so it does not regenerate or re-symlink Bureau startup context after cleanup.
2. Fix `output_style` path transport so paths with spaces are preserved correctly.

### Should-fix

1. Fix Claude cleanup so it does not create an empty settings file unnecessarily.
2. Add a real bare-mode integration test.
3. Add a regression test for `output_style` paths containing spaces.
4. Add a cleanup test for the “Claude settings file did not previously exist” case.

### Nice-to-have

1. Replace more handcrafted deployment-test snippets with tests that exercise the real scripts or higher-level setup flow.
2. Add a live smoke-test checklist for supported CLIs:

    - normal mode
    - update mode
    - bare mode

## Decision guidance

The feature is close, but it should **not** be considered fully hardened yet.

- If the goal is “feature implemented and locally testable,” the current state is good.
- If the goal is “bulletproof and ready to rely on operationally,” the three issues above should be fixed first, especially the bare-mode and path-splitting problems.
