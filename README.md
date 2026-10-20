# Lark Suite skills mirror

An unofficial, versionable mirror of the official Lark/Feishu aggregated
`lark-suite` skill. Skill content is downloaded from the official distribution;
this repository does not generate or modify the guides.

## Layout

```text
lark-suite/
├── SKILL.md
└── references/
    └── lark-*/
        ├── GUIDE.md
        └── ...
```

Only `lark-suite/` should be installed into an agent's skills directory.

## Automatic updates

The GitHub Actions workflow runs every day at **03:23 UTC (11:23 China time)**,
and can also be started through **Actions → Sync official Lark Suite skills →
Run workflow**. Scheduled runs use the default branch and may be delayed by
GitHub. GitHub can disable schedules on inactive public repositories.

The workflow reads the official discovery index:

<https://open.feishu.cn/lark-cli/skills/isolated/.well-known/agent-skills/index.json>

It downloads the archive named there, verifies its SHA-256 digest, checks archive
paths and file types, and replaces the mirrored tree, including upstream
deletions. Only content changes create a commit. Failed downloads or validation
leave the previous mirror intact.

Push this repository to GitHub and enable Actions. The workflow requests
`contents: write`; organization policies and branch protection must permit the
Actions bot to push to the default branch. No personal access token is required.

## Manual sync

Requires [uv](https://docs.astral.sh/uv/). Python 3.12 is provisioned by uv.

```sh
uv run --python 3.12 --no-project python -m unittest discover -s tests -v
uv run --python 3.12 --no-project python scripts/sync.py
git diff --stat
```

## Reproducible consumption with Nix

Pin this repository to a full commit SHA with `pkgs.fetchFromGitHub`, then use
`${src}/lark-suite` as the skill directory. Each sync commit preserves a snapshot
even when the upstream rolling URL changes.

## Provenance

Upstream project: <https://github.com/larksuite/cli> (MIT licensed).
This is not an official Lark distribution repository. Mirrored content retains
its upstream ownership and applicable license.
