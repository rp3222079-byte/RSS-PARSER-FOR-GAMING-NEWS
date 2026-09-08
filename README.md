# RSS → Telegram gaming news bot

Checks a list of RSS feeds on a schedule and posts new articles to your
Telegram channel, running for free on GitHub Actions.

## How it works

- `feeds.txt` — the RSS feeds you're watching (one URL per line)
- `rss_to_telegram.py` — fetches each feed, figures out what's new, posts it
- `state.json` — remembers what's already been posted (created automatically,
  committed back to the repo after every run so state persists between runs)
- `.github/workflows/rss-telegram.yml` — runs the script every 30 minutes

On the very first run, each feed is "seeded" — its current articles are
recorded as already-seen but NOT posted, so your channel doesn't get flooded
with the entire back-catalog the moment you turn this on.

## Setup

### 1. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Save the token it gives you (looks like `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

### 2. Add the bot to your channel

1. Open your channel → **Administrators** → **Add Administrator**
2. Add your bot, and give it permission to post messages

### 3. Get your channel's chat ID

- **Public channel** (has a `@username`): you can just use `@yourchannelname` as the chat ID — no lookup needed.
- **Private channel**: post any message in the channel, forward it to [@userinfobot](https://t.me/userinfobot), and it will show you the chat ID (a negative number starting with `-100`).

### 4. Create a GitHub repo with these files

Create a new repo and upload all the files in this folder (keep the
`.github/workflows/` folder structure intact).

### 5. Add your secrets

In the repo: **Settings → Secrets and variables → Actions → New repository secret**

- `TELEGRAM_BOT_TOKEN` = the token from BotFather
- `TELEGRAM_CHAT_ID` = your channel's `@username` or numeric ID

### 6. Allow the workflow to commit

**Settings → Actions → General → Workflow permissions** → select
**"Read and write permissions"** → Save.
(This lets the workflow save `state.json` back to the repo after each run.)

### 7. Test it

Go to the **Actions** tab → **RSS to Telegram** → **Run workflow** to trigger
it manually. Check the run logs — the first run should say "Seeded ... (no
posts sent)" for each feed. Run it a second time (or just wait 30 minutes)
and any genuinely new articles should appear in your channel.

## Customizing

- **Add/remove sources**: edit `feeds.txt`, one URL per line.
- **Change how often it checks**: edit the `cron` line in the workflow file. `*/30 * * * *` = every 30 min. GitHub's actual scheduling can lag behind this during high load — treat it as "roughly this often," not exact.
- **Change the message format**: edit `format_message()` in `rss_to_telegram.py` — e.g. add your own emoji, hashtags, or a "what we think" line.
- **Limit spam bursts**: `MAX_NEW_POSTS_PER_FEED` in the script caps how many posts go out per feed per run, in case a site publishes a big batch at once.

## Verifying a feed URL

Sites occasionally move their RSS paths. To check a URL still works, paste it
straight into a browser — you should see raw XML with `<item>` or `<entry>`
blocks, not a webpage or a 404. To find a feed for a new site, check its
footer for an RSS icon, or search `"[site name] rss feed"`.

## Running locally (optional, for testing)

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="@yourchannel"
python rss_to_telegram.py
```
