---
name: kamaji
description: Conventions for any app that stores data on kamaji, Harsh's home server — one Postgres database per app, <app>_authenticator + <app>_anon roles, a PostgREST per app behind the kamaji Cloudflare Tunnel, dbmate migrations in the app's repo, kamaji as production only (tests use a throwaway local Postgres), and a manual deploy script. Source of truth is the harshagrawal13/kamaji-server repo. Use when a project needs a database or API, when adding an app to kamaji, writing or applying a migration, deploying to kamaji, wiring PostgREST or Cloudflare Access, writing tests that touch a database, or when the user says "kamaji", "put this on kamaji", "add a database", or "/kamaji".
argument-hint: "[what the app needs, or: add-app <name> | migrate | deploy <name> | check]"
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash(gh:*), Bash(git:*), Bash(ssh:*), Bash(dbmate:*), Bash(psql:*), AskUserQuestion
---

# kamaji

kamaji is Harsh's always-on Mac. It hosts every app's data in one Postgres cluster.
This skill keeps each project consistent with that setup and stops it from inventing
its own.

## Input

<arguments>
$ARGUMENTS
</arguments>

## Step 0 — Read the source of truth first

The conventions below are a summary. **harshagrawal13/kamaji-server is authoritative**,
and its app table (ports, hostnames, databases) is only there. Read it before
deciding anything:

- a local checkout at `~/Developer/personal/kamaji-server` (`git -C … pull --ff-only` first), or
- `gh api repos/harshagrawal13/kamaji-server/contents/README.md -q .content | base64 -d`,
  plus `apps.toml` once it exists.

If the README contradicts this skill, the README wins. Tell the user this skill has
drifted and needs a polish bump.

## Conventions

- **One database per app**, named after the app. Nothing crosses databases: one app
  reads another's data only through that app's public HTTP API, and never writes to it.
- **kamaji is production only.** No `<app>_test` databases, and no test ever connects to
  kamaji. Tests use either:
  - an in-process fake of the API, for fast offline tests, or
  - a throwaway local Postgres + PostgREST built from the app's migrations, which skips
    cleanly when they aren't installed (`brew install postgresql@18 postgrest dbmate`).
- **Roles are prefixed with the app**, because roles are cluster-wide:
  - `<app>_authenticator`: `login noinherit`, no privileges of its own. Its password
    lives only in `~/.config/postgrest/<app>.conf` on kamaji. Never in git, never in chat.
  - `<app>_anon`: what PostgREST switches to. It has exactly the grants the API needs,
    and they're written in the app's migrations.
  - Objects are owned by the `harsh` superuser, and there's no owner role. Each
    database gets `revoke connect ... from public`.
- **One PostgREST per database**, on its own 127.0.0.1 port, taken from kamaji-server's
  app table. PostgREST serves only at `/`, so an app that wants one origin proxies
  `/api/*` itself.
- **An API that writes sits behind Cloudflare Access, and the origin checks the
  `Cf-Access-Jwt-Assertion` token as well** (signature, `aud`, `exp`, email), failing
  closed when that isn't configured. An API can be public only if it's read-only.
- **Schema changes are dbmate migrations** in the app's repo under `db/migrations/`
  (`-- migrate:up` / `-- migrate:down`). A migration that has been applied is never edited.
- **Where things live:**
  - kamaji-server knows that an app exists: its database, roles, port, hostname,
    launch agents and deploy steps.
  - The app's repo knows what's inside its database: migrations, grants and code.
  - Apps never vendor kamaji-server; no submodules.
- **Backups:** the nightly `pg_dump` of every database plus `pg_dumpall --globals-only`,
  kept 30 days on Google Drive. A new database is covered automatically; check this
  rather than assuming it.

## Routes

**Designing storage for a project.** Apply the conventions above. Then propose:
- the database name;
- the tables, and the `api` schema views PostgREST will serve;
- the exact grants to `<app>_anon`;
- the test strategy.

Write the first migration in the app's repo. Don't touch kamaji.

**`add-app <name>`.** Use kamaji-server's `add-app` script if it exists. If it doesn't
yet, list the steps and let the user run them:
- create the database;
- create both roles and generate the password into the conf file;
- `revoke connect`;
- the PostgREST launch agent;
- the tunnel hostname;
- a row in the app table.

Anything done by hand gets written back into kamaji-server in the same session.

**`migrate` / `deploy <name>`.** Use kamaji-server's `deploy` script (`git pull --ff-only`,
`dbmate up`, restart the agents, smoke check). Show the pending migrations first
(`dbmate status`).

**`check`.** Compare what's running with kamaji-server: databases, roles, launch agents,
tunnel hostnames and ports. Report every drift in either direction, and change nothing.

## Rules

- **Anything that changes kamaji needs a clear yes from the user first**, stating
  exactly what will run. That covers `ssh kamaji` with `psql`, `dbmate up`, `launchctl`,
  and tunnel or Access changes.
- **Reading is fine without asking**: `\l`, `\du`, `dbmate status`, `launchctl list`.
- **Never read, print or copy PostgREST passwords or `~/.config/postgrest/*.conf`
  contents**, and never commit them.
- **Cloudflare Access applications are created by Harsh in the dashboard.** Give the
  exact settings; don't try to do it. Create the Access application *before* its
  hostname is added to the tunnel.
- **Fail loudly.** If kamaji is unreachable or reality differs from kamaji-server, say
  so verbatim. Don't guess ports, roles or hostnames.
