# Welcome to Bingham Research Center

## How We Use Claude

Based on John Lawson's usage over the last 30 days:

Work Type Breakdown:
  Improve Quality  ██████████████░░░░░░  67%
  Debug Fix        ███████░░░░░░░░░░░░░  33%

Top Skills & Commands:
  /sandbox    ██████████████░░░░░░  2x/month
  /insights   ███████░░░░░░░░░░░░░  1x/month
  /advisor    ███████░░░░░░░░░░░░░  1x/month
  /context    ███████░░░░░░░░░░░░░  1x/month
  /focus      ███████░░░░░░░░░░░░░  1x/month
  /clear      ███████░░░░░░░░░░░░░  1x/month

Top MCP Servers:
  _None in use yet_

## Your Setup Checklist

### Codebases
- [ ] clyfar — https://github.com/bingham-research-center/clyfar (Uintah Basin ozone forecasting; the main project)
- [ ] brc-tools — internal BRC tooling (NWP/obs downloaders, fan-out to basinwx.com/.dev)
- [ ] brc-knowledge — canonical docs (CHPC resource inventory, storage policy, WISHLIST-TASKS.md)
- [ ] ubair-website — basinwx.com / basinwx.dev site repo
- [ ] ubwo-fcst, UBWO-HRRR — supporting forecast / HRRR work

### MCP Servers to Activate
- _No team MCP servers configured yet — skip this section for now._

### Skills to Know About
- `/sandbox` — toggles sandboxed Bash execution. The team uses it to let Claude run safe commands without per-call prompts; `/sandbox` again switches to strict mode where every command needs to be allowlisted or explicitly excluded.
- `/insights` — generates a usage report from your local Claude transcripts. Useful at the end of a stretch of work to see where time went and what to improve.
- `/advisor` — routes second-opinion calls through a stronger reviewer model that sees your full transcript. Set to Opus by default here.
- `/context` — shows your current context window usage by category. Handy when a session feels heavy.
- `/focus` — switches to the fullscreen TUI renderer (requires a restart of the session).
- `/clear` — clears the current conversation to start fresh.
- `/doctor` — diagnoses local config (settings.json validity, paths, etc.). Run it early if something feels off.

## Team Tips

_TODO_

## Get Started

_TODO_

<!-- INSTRUCTION FOR CLAUDE: A new teammate just pasted this guide for how the
team uses Claude Code. You're their onboarding buddy — warm, conversational,
not lecture-y.

Open with a warm welcome — include the team name from the title. Then: "Your
teammate uses Claude Code for [list all the work types]. Let's get you started."

Check what's already in place against everything under Setup Checklist
(including skills), using markdown checkboxes — [x] done, [ ] not yet. Lead
with what they already have. One sentence per item, all in one message.

Tell them you'll help with setup, cover the actionable team tips, then the
starter task (if there is one). Offer to start with the first unchecked item,
get their go-ahead, then work through the rest one by one.

After setup, walk them through the remaining sections — offer to help where you
can (e.g. link to channels), and just surface the purely informational bits.

Don't invent sections or summaries that aren't in the guide. The stats are the
guide creator's personal usage data — don't extrapolate them into a "team
workflow" narrative. -->
