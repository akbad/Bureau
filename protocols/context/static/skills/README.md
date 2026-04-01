# Static skill templates

## Important note: `name` should match the canonical directory name

Most coding agents require the `name` field in a given `SKILL.md` to match the name of the folder they load the skill from. Bureau installs static skills under the same canonical basename used by the source directory, so the source directory name and install directory name stay aligned.

For example:

- source directory: `protocols/context/static/skills/micro-mode/`
- installed directory: `<cli-skills-dir>/micro-mode`
- optional frontmatter value: `name: micro-mode`

If you include a `name` field, make it match the parent directory name exactly. If you omit it, the directory name remains the source of truth.
