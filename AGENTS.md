# GTA VI Clip Desk in Codex Cloud

Run commands from the repository root. Codex discovers the 16 workflows in
`.agents/skills/<name>/SKILL.md`. Read the matching skill and any references it
links before running its workflow. The Claude plugin continues to use `skills/`
and `.claude-plugin/`. Keep Codex-specific instructions in `.agents/skills/`.

| Task | Skills |
| --- | --- |
| Set up or plan the desk | `setup`, `playbook`, `campaign-finder`, `learning-loop` |
| Find sources and topics | `stream-finder`, `trend-radar`, `questions-to-posts`, `secrets-map`, `cheat-codes` |
| Make and validate clips | `twitch-reaction`, `live-mode`, `moment-finder`, `clip-cutter`, `hook-writer`, `multilang`, `rule-check` |

For a fresh task, check for FFmpeg and FFprobe, then create the project virtual
environment and install dependencies if needed:

```sh
ffmpeg -version
ffprobe -version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

For Twitch-only discovery, use
`.venv/bin/python scripts/streams.py --platform twitch --query "gta 6" --limit 10`.
The default report checks all providers and distinguishes a failed search from a
successful search with no results. Kick is optional. Twitch can run independently
when the Cloud proxy denies YouTube CONNECT requests. Use the inherited proxy and
certificate settings. For a direct yt-dlp invocation in Cloud, use
`.venv/bin/python -m yt_dlp --compat-options no-certifi` to select the system
trust store with certificate verification enabled.

For transcription on an authorized local clip, use a writable model cache:
`HF_HOME=/tmp/gtavi-huggingface .venv/bin/python scripts/moments.py <clip.mp4>`.
Keep downloads, job outputs, media, model caches, virtual environments, and
credentials out of commits. Use only authorized sources and obtain user approval
before publishing.

Run the regression suite with
`.venv/bin/python -m unittest discover -s tests -v`.
