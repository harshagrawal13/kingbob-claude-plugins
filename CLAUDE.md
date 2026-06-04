# kingbob-claude-plugins

Harsh's personal Claude Code plugin. One plugin (`kingbob`), skills under `skills/<skill-name>/SKILL.md`.

## Release workflow — required for every user-visible change

Whenever a PR (or direct commit to `main`) adds, replaces, or meaningfully changes a skill, it MUST also:

1. **Bump the version** in `.claude-plugin/plugin.json`.

   Bump rule against the current value `X.Y.Z`. The third component is always `0` — it is never incremented.
   - **Polish to an existing skill** (docs, behavior tweaks, bug fixes, new capability inside an existing skill): bump the middle component → `X.Y.0` → `X.(Y+1).0`.
   - **New skill added** (a new directory under `skills/`): bump the leading component and reset the middle → `X.Y.0` → `(X+1).0.0`.

   There is no patch slot on purpose: urgent fixes ride the next polish bump.

2. **Cut a GitHub release** matching the new version once the change is on `main`:

   ```
   gh release create vX.Y.0 --title "vX.Y.0" --generate-notes
   ```

   The tag must equal the `plugin.json` version prefixed with `v`. Do not let `main` drift ahead of the last release tag.

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter: `name` (must equal the directory name), `description` (include trigger phrases — it's how Claude decides to invoke), optional `argument-hint`, `user-invocable: true`, and a minimal `allowed-tools` list.
2. Document it in `README.md` under **Skills** (invocation line + "What it does" list).
3. Run `python3 scripts/validate.py`.
4. Bump the version (new skill → major bump) and release per the rules above.

## Conventions

- Skills are invoked as `/kingbob:<skill-name>`.
- Keep `allowed-tools` tight — e.g. `Bash(curl:*)` rather than `Bash`.
- Skills must fail loudly: if an external lookup returns garbage, report it verbatim rather than fabricating output.
- CI (`.github/workflows/validate.yml`) runs `scripts/validate.py` on every PR and push to `main`.
