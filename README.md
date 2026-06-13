# Ember — Discord Bot

All-in-one community bot with levels, automod, moderation, tickets and giveaways.

## Features

- **Levels**: XP per message, level-up announcements, `/rank` card (Pillow), `/leaderboard`
- **Automod**: spam detection, caps ratio, invite filter — 3 warnings = 10min timeout
- **Moderation**: `/warn`, `/warnings`, `/clear`
- **Tickets**: button panel, private channel per user, close button cleanup
- **Giveaways**: `/giveaway 1h prize`, button entries, auto draw, `/reroll`

## Tech Stack

Python · discord.py 2.x · SQLite · Pillow · Slash commands

## Run

```bash
pip install -r requirements.txt
copy .env.example .env   # add your bot token
python bot.py
```
