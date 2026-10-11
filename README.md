# Follower Sensei

A Claude plugin for Instagram audience analysis, built for creators, producers and SMM specialists. It compares what an account is about and what it wants to achieve with who actually follows it and how the audience is changing — then points out mismatches and anomalies and gives recommendations.

## How it works

0. **Getting started** (`start`) — a short welcome and four questions about the account, shown when the user arrives without a specific task.
1. **Account and goals** (`account-brief`) — what the account is about, what it wants to achieve and who it is for; its core message, tone of voice, values and positioning; an account card the other steps build on.
2. **Follower analysis** (`audience-analysis`) — who follows the account now (profile types, fields, language, suspicious accounts — saved to an Excel file with a confidence level and profile links for manual review, plus a separate tab of accounts that are probably real) and how the audience is changing (new followers and unfollowers, growth and churn), compared with the account's goals: is the audience moving where it should, and are there anomalies — for example, the wrong people arriving or key followers leaving.

Then, offered by the plugin and only with the user's agreement:

- **Strategy** (`strategy`) — built step by step, each step shown for edits. Takes into account the account's tone of voice, values and positioning, and starts by choosing a direction: shift to a different audience, grow the current one, or increase its engagement.
- **Content** (`content`) — after the strategy is confirmed: content plan, captions, Reels and Stories scripts.
- **Report** (`report`) — for a period, as text or a PDF file.

Skills turn on by themselves when a request fits, or manually: `/follower-sensei:audience-analysis` and so on. The plugin's instructions are in English; Claude answers in the user's language.

## What files it uses

Instagram doesn't show who exactly followed or unfollowed an account over a period — only the current list and overall numbers. The only way to find out is to compare follower lists saved on different dates. The plugin accepts:

- **a current follower list** — with names, profile links or usernames;
- **a table with statuses** — where each follower is marked as new, unfollowed or stayed;
- **or two lists from different dates** — the plugin compares them itself.

CSV files from any service work: the delimiter, encoding and columns are detected automatically, and the plugin asks the user about status values it doesn't recognize.

## Relationship with the Follower Tracker extension

The plugin's author is the developer of the Chrome extension [Follower Tracker](https://chromewebstore.google.com/detail/follower-tracker/onejjehablkibkmocglgkbjfphlnilan?utm_source=claude&utm_medium=plugin&utm_campaign=readme). It saves the follower list as CSV and, when earlier lists exist, a table with the statuses `recent follow`, `unfollowed` and `stayed`.

The plugin recommends the extension only when follower data is missing for the task at hand. Using it is optional: the plugin works with files from other services, and strategy and content work without any exports.

Links to the extension in the plugin carry UTM tags (`utm_source=claude`, `utm_medium=plugin`, `utm_campaign` — the place in the plugin; `report-document` — the link inside a finished report). They are a label in the link address used for Chrome Web Store page-view statistics; the plugin doesn't collect or send any data.

## What the plugin runs and where data goes

- The plugin consists of instructions for Claude (`skills/*/SKILL.md`) and one Python script: `skills/audience-analysis/scripts/audience.py`.
- The script uses only the Python standard library, runs locally on CSV files the user provides, and **sends nothing to the network and downloads nothing from it**. It computes summaries, compares lists and can save results to files in the working folder.
- To save the suspicious-accounts file as Excel (.xlsx), the script uses the openpyxl library if it's already installed; otherwise it saves CSV files. For PDF reports, Claude uses whatever tools are available in the user's environment. The plugin doesn't install packages itself.
- The plugin has no hooks, MCP servers or external dependencies.
- The plugin doesn't access Instagram and forbids Claude from collecting data from profiles automatically: that breaks Instagram's rules and personal data laws. The audience is analyzed as a whole, with no profiles of individual people.

## Where account data is kept

In Claude Code the plugin suggests keeping everything for an account in the working folder:

```
accounts/
└── account-name/
    ├── card.md               # what the account is about, goals, core message, tone, values, positioning
    ├── strategy.md
    ├── content-plan-10.md
    ├── snapshots/
    │   ├── 2026-10-01-followers.csv
    │   └── 2026-11-01-followers.csv
    └── reports/
```

On claude.ai it's easier to create a separate project per account. Follower analysis and PDF reports on claude.ai need code execution turned on; without it, Claude reads the CSV by hand, less precisely, and gives the report as text.

## Installation

On claude.ai or in Claude Desktop: **Customize → Plugins → Add → Add marketplace**, then the repository link: `https://github.com/evv22081989-ai/follower-sensei`

In Claude Code:

```
/plugin marketplace add evv22081989-ai/follower-sensei
/plugin install follower-sensei@follower-sensei-marketplace
```

## Example files

The `examples/` folder holds test data with made-up accounts:

- `followers-2026-09-01.csv`, `followers-2026-10-01.csv` — two follower lists from different dates;
- `follower-changes-2026-10-01.csv` — a status table in the Follower Tracker format;
- `other-service-changes.csv` — a table from "another service": different column names, usernames instead of links, `;` delimiter, Windows-1251 encoding and one unfamiliar status value.

## Privacy

The plugin sends no data anywhere and has no server; see the full [Privacy Policy](PRIVACY.md).

## License

MIT, see [LICENSE](LICENSE).
