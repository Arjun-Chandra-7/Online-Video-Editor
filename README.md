# Viralist Editor— agent-native video editor

Viralist is a local, non-linear video editor designed to be easier for an AI agent to operate than a GUI made for the main project called Viralyst. One MCP connection gives an agent structured timeline inspection, deterministic edits, semantic diffs, dry runs, atomic batches, snapshots, undo/redo, captions, voiceover, pacing analysis, project persistence, and hardware-aware MP4 export. A browser UI at `http://localhost:8080` stays synchronized for human review.

The MCP is the product interface—not a demo wrapper. It and the web UI mutate the same live `TimelineEngine`, so an agent never edits an invisible second copy of the project.

## What an agent can do

- Discover capabilities, accepted enums, limits, and current project revision.
- Inspect tracks, clips, assets, captions, word timestamps, markers, keyframes, effects, transforms, grading, and audio state.
- Import local video/audio/images; place, split, trim, move, duplicate, speed-change, reverse, freeze, or ripple-delete clips.
- Add/remove/reorder/mute/lock/hide tracks.
- Apply transforms, keyframes, 25 creator effects, LUTs, transitions, gain, pan, fades, and speech enhancement.
- Create/edit/delete styled captions; search transcripts; return SRT; remove silences/filler words using timestamps.
- Generate neural narration and synchronized kinetic captions using 11 voice presets.
- Create snapshots, run preview-only edits, commit atomic batches, inspect semantic diffs, and undo/redo.
- Audit pacing, hooks, retention risks, caption coverage, and energy.
- Save portable project JSON and render MP4 with NVIDIA, Intel Quick Sync, or CPU encoding.

The complete operating contract is in [SKILL.md](SKILL.md). Agent tool and workflow details are in [references/TOOL_REFERENCE.md](references/TOOL_REFERENCE.md) and [references/WORKFLOWS.md](references/WORKFLOWS.md).

## Install

Requirements: Python 3.11+, Node.js 20+, npm, and FFmpeg.

```bash
git clone https://github.com/Arjun-Chandra-7/Online-Video-Editor.git
cd Online-Video-Editor
./scripts/setup.sh
```

Start the web editor manually:

```bash
./scripts/start_editor.sh
```

Open `http://localhost:8080`. API health is available at `http://localhost:8080/api/status`.

## Give it to an agent

Viralist uses MCP over stdio and auto-starts the web editor if it is offline. Use absolute paths in client configuration.

### Codex CLI

```bash
codex mcp add viralist --env VIRALIST_AUTOSTART_WEB=true -- /absolute/path/Online-Video-Editor/.venv/bin/python /absolute/path/Online-Video-Editor/backend/mcp_server.py
codex mcp list
```

For project-scoped configuration, create `.codex/config.toml`:

```toml
[mcp_servers.viralist]
command = "/absolute/path/Online-Video-Editor/.venv/bin/python"
args = ["/absolute/path/Online-Video-Editor/backend/mcp_server.py"]
cwd = "/absolute/path/Online-Video-Editor"
startup_timeout_sec = 45
tool_timeout_sec = 900
required = true
default_tools_approval_mode = "writes"
env = { VIRALIST_AUTOSTART_WEB = "true" }
```

Codex supports stdio MCP servers, reads the server's `instructions`, and supports project-level MCP configuration. See the [official OpenAI MCP documentation](https://developers.openai.com/codex/mcp/).

### Claude Desktop, Cursor, or another stdio MCP client

Add the equivalent entry to that client's MCP configuration:

```json
{
  "mcpServers": {
    "viralist": {
      "command": "/absolute/path/Online-Video-Editor/.venv/bin/python",
      "args": ["/absolute/path/Online-Video-Editor/backend/mcp_server.py"],
      "env": { "VIRALIST_AUTOSTART_WEB": "true" }
    }
  }
}
```

Then give the agent this repository's `SKILL.md` and ask:

> Inspect the Viralist project, snapshot it, preview your proposed edit as one atomic batch, commit after checking the diff, run pacing QA, and export the final MP4.

The MCP also publishes `viralist://skill`, `viralist://project`, and `viralist://capabilities` as resources, so compatible clients can retrieve context directly.

## Agent-first safety

All dedicated destructive tools default to `dry_run=true`. A dry run executes against a temporary copy and returns the exact semantic diff without changing the timeline. `edit_batch` supports up to 100 operations, commits as one undo step, and rolls back all state and imported files if any operation fails. Stable IDs prevent ambiguous natural-language targeting.

Typical flow:

```text
discover → inspect IDs → snapshot → dry-run batch → review diff → commit → inspect/audit → save/export
```

## Architecture

```text
MCP client ──stdio──> backend/mcp_server.py ──HTTP──> AgentService
                                                        │
Browser UI <──WebSocket + REST── FastAPI <────── shared TimelineEngine
                                                        │
                                      assets / project JSON / FFmpeg export
```

The MCP can attach to an already-running API using `VIRALIST_API_URL`. Otherwise it starts FastAPI in-process on localhost, allowing one MCP command to provide both agent tools and the review UI.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `VIRALIST_API_URL` | `http://127.0.0.1:8080/api` | Attach MCP to a specific live editor API. |
| `VIRALIST_AUTOSTART_WEB` | `true` | Auto-start the local web/API process from MCP. |
| `PORT` | `8080` | Port used by manual web startup. |

## Development and validation

```bash
source .venv/bin/activate
python -m compileall -q backend
cd frontend && npm run build && cd ..
python scripts/mcp_smoke_test.py
```

Runtime media, exports, saved projects, previews, models, caches, and secrets are intentionally excluded from Git. Empty storage directories are retained. See [EDITOR_AUDIT.md](EDITOR_AUDIT.md) for the feature and implementation audit.
