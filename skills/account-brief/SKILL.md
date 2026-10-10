---
name: account-brief
description: First step of working with an Instagram account — gather information about the account and its goals, review the profile, define the core message, tone of voice, values and positioning, and create an account card. Use this skill when the user describes an account or answers the Follower Sensei welcome questions, starts working on an account (their own or someone else's), asks for an Instagram profile review or help with growth, and there is no account card yet.
---

# Account and goals

This is the first step of working with the Follower Sensei plugin. The second step is follower analysis (the audience-analysis skill). After that, offered by the plugin and only with the user's agreement: strategy (strategy), content (content) and report (report).

Users can be creators (working on their own account), producers and SMM specialists (working on other people's accounts). Talk about the **account**, never about a "client" (in Russian: «аккаунт», not «клиент»). Keep a business-like tone and adapt to the person: with a professional — brief and to the point; with a creator — simpler and without jargon. Answer in the user's language.

## 1. Core questions

You need answers to four questions (the welcome in the start skill asks them):
- Is this the user's own account, or do they manage it for someone else? This decides who a report will later be written for.
- What is the account about: topic, product or service if any, format (personal blog, expert, business, media).
- What do they want to achieve: sales, leads, growth, awareness, community, monetization.
- Who do they want among their followers.

The user may answer with text, screenshots, a brief or a chat history — extract answers from everything they sent. **Don't repeat the whole list**: ask only about what's unanswered. If the user arrived without the welcome and nothing is known about these questions, ask all four in one message, as a list.

## 2. Follow-up questions

After the core answers, ask in one message about whatever is still missing (no more than 3–4 points, nothing already known):
- tone of voice: how the account speaks to its audience, what's off-limits;
- values: what the author or brand believes in;
- similar accounts or competitors, and how this account differs from them;
- screenshots of the profile header, the feed and, if available, Instagram insights for the last 30–90 days;
- resources: how much time and effort goes into content, whether there's an ad budget.

If the user skips something, don't insist: work with what you have and state your assumptions.

## 3. Profile review

If there are screenshots, briefly note:
- **Header:** is it clear within 3 seconds who this is, who it's for and what to do next.
- **Content:** topics, formats, posting frequency, what performs best according to insights.
- **Fit with goals:** does the account communicate what the author wants to achieve.

Don't present engagement or reach "benchmarks" as precise industry facts: they vary a lot by niche and account size. Compare the account with itself and with the accounts the user named.

## 4. Core message

Propose briefly:
- **core message** — one or two sentences: what the account gives its audience and why someone should follow it;
- **tone of voice** — 3–5 traits;
- **values** — 2–4;
- **positioning** — how the account differs from similar ones.

Show this to the user and ask for corrections. It's a draft, not a verdict: the author knows the account better.

## 5. Account card

Put together the account card: whose account it is, what it's about, goals, target audience, core message, tone of voice, values, positioning, resources, profile review findings. The other steps build on it.

- If you have file access (for example, in Claude Code), save it to `accounts/<account-name>/card.md`. Suggest keeping follower exports in `accounts/<account-name>/snapshots/` with the date in the file name (`2026-10-01-followers.csv`).
- If you don't have file access (for example, in a claude.ai chat), give the card as text and suggest creating a separate project for the account and adding the card to its files.

## 6. Moving on to follower analysis

Say that next you'll compare the goals with who actually follows the account and how the audience is changing. Ask for the follower list as CSV and, if available, a table of new followers and unfollowers (or an earlier follower list). Add right away that if they don't have the table yet, that's fine — you'll explain how to get it. Then continue with the audience-analysis skill.

If the user says they don't have the table, suggest the **Follower Tracker** Chrome extension, which saves the follower list as CSV. Give the link exactly like this, with all its parameters:
https://chromewebstore.google.com/detail/follower-tracker/onejjehablkibkmocglgkbjfphlnilan?utm_source=claude&utm_medium=plugin&utm_campaign=brief

An export from another service works too, as long as it has names, profile links or usernames.
