# Privacy Policy — Follower Sensei

*Last updated: October 11, 2026*

Follower Sensei is a plugin for Claude made by Elena Vyazovetskova. This policy explains what data the plugin works with and what happens to it.

## The short version

The plugin has no server and no backend. It doesn't send any data to the author or to any third party, and the author never receives, sees or stores your data.

## What data the plugin works with

- **Information about an Instagram account** that you share in the conversation: what the account is about, its goals, tone of voice, screenshots of the profile and of Instagram insights.
- **Follower lists** that you provide as CSV files — usually profile names, usernames and profile links of followers, new followers and unfollowers. These lists can contain personal data of the people who follow the account.

The plugin works only with data you provide. It doesn't access Instagram, doesn't open profiles and doesn't collect data from the internet.

## How the data is processed

- The plugin is a set of instructions for Claude plus one Python script (`skills/audience-analysis/scripts/audience.py`). The script runs in your own environment — on your computer in Claude Code, or in Claude's sandbox on claude.ai — and **sends nothing to the network**.
- Results are shown in the conversation and, when useful, saved as files in your working folder or chat: for example, an account card, lists of new followers and unfollowers, a file of suspicious accounts, a report. These files stay with you; you can delete them at any time.
- The analysis looks at the audience as a whole. The plugin doesn't build profiles of individual followers.

## Claude itself

Your conversations with Claude, including the files you share, are handled by Anthropic under its own terms and privacy policy: https://www.anthropic.com/legal/privacy. This plugin doesn't change how Anthropic processes your data.

## Links in the plugin

Some messages and reports contain a link to the Follower Tracker Chrome extension (by the same author). The link carries UTM tags (`utm_source`, `utm_medium`, `utm_campaign`), which only show the author, in Chrome Web Store statistics, how many people opened the extension's page from the plugin. Opening the link doesn't send any of your data or your followers' data.

## Your responsibility for follower data

Follower lists contain other people's data. Use the plugin's results for analyzing your own or your clients' accounts, store the files securely, and don't use them to contact, profile or track individual people.

## Changes

If this policy changes, the new version will be published in this file, with the date at the top.

## Contact

Questions about this policy: open an issue in this repository — https://github.com/evv22081989-ai/follower-sensei/issues
