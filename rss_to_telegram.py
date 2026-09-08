#!/usr/bin/env python3
"""
RSS -> Telegram bot for a gaming news channel.

Reads a list of RSS feed URLs from feeds.txt, checks each one for entries
that haven't been posted yet (tracked in state.json), and sends the new
ones to a Telegram channel via the Bot API.

Designed to be run repeatedly (e.g. every 30 min via GitHub Actions cron).
On the very first run for a given feed, it "seeds" state.json with the
current entries WITHOUT posting them, so you don't dump the entire feed
history into your channel the first time it runs.
"""

import html
import json
import os
import sys
import time
from pathlib import Path

import feedparser
import requests

FEEDS_FILE = Path("feeds.txt")
STATE_FILE = Path("state.json")

BOT_TOKEN = os.environ.get("8805890853:AAGXUzfNVPTHlEjNzID3ShVlE58fABkXVno")
CHAT_ID = os.environ.get("@IgroVestnikRU")

MAX_SEEN_PER_FEED = 200      # how many old entry ids to remember per feed
MAX_NEW_POSTS_PER_FEED = 8   # safety cap per run, in case a feed dumps a lot at once
REQUEST_TIMEOUT = 15
SEND_DELAY_SECONDS = 2       # be gentle with Telegram's rate limits


def load_feeds():
    if not FEEDS_FILE.exists():
        print(f"ERROR: {FEEDS_FILE} not found", file=sys.stderr)
        sys.exit(1)
    urls = []
    for line in FEEDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def entry_id(entry):
    # Prefer the feed's own guid/id, fall back to the link
    return entry.get("id") or entry.get("link")


def strip_html(text):
    # very small helper for summaries that include HTML
    import re
    text = re.sub("<[^<]+?>", "", text or "")
    return html.unescape(text).strip()


def format_message(source_name, entry):
    title = strip_html(entry.get("title", "")).strip()
    link = entry.get("link", "")
    summary = strip_html(entry.get("summary", ""))
    if len(summary) > 300:
        summary = summary[:300].rsplit(" ", 1)[0] + "…"

    msg = f"🎮 <b>{html.escape(title)}</b>\n\n"
    if summary:
        msg += f"{html.escape(summary)}\n\n"
    msg += f"📰 {html.escape(source_name)}\n{link}"
    return msg


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, data=payload, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        print(f"Telegram API error {resp.status_code}: {resp.text}", file=sys.stderr)
    return resp.status_code == 200


def main():
    if not BOT_TOKEN or not CHAT_ID:
        print(
            "ERROR: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables",
            file=sys.stderr,
        )
        sys.exit(1)

    feeds = load_feeds()
    state = load_state()
    total_sent = 0

    for feed_url in feeds:
        parsed = feedparser.parse(feed_url)
        if parsed.bozo and not parsed.entries:
            print(f"WARNING: could not parse {feed_url}: {parsed.bozo_exception}")
            continue

        source_name = parsed.feed.get("title", feed_url)
        seen = set(state.get(feed_url, []))
        is_first_run_for_feed = feed_url not in state

        # feedparser returns newest-first; reverse so we post oldest-new first
        entries = list(reversed(parsed.entries))

        new_ids = []
        posts_this_feed = 0

        for entry in entries:
            eid = entry_id(entry)
            if not eid or eid in seen:
                continue

            new_ids.append(eid)

            if is_first_run_for_feed:
                # seed only, don't spam the channel with the whole feed
                continue

            if posts_this_feed >= MAX_NEW_POSTS_PER_FEED:
                continue

            message = format_message(source_name, entry)
            if send_to_telegram(message):
                posts_this_feed += 1
                total_sent += 1
                time.sleep(SEND_DELAY_SECONDS)

        if is_first_run_for_feed:
            print(f"Seeded {source_name} with {len(new_ids)} existing entries (no posts sent).")
        else:
            print(f"{source_name}: sent {posts_this_feed} new post(s).")

        seen.update(new_ids)
        # keep the seen-set from growing forever
        state[feed_url] = list(seen)[-MAX_SEEN_PER_FEED:]

    save_state(state)
    print(f"Done. Total messages sent this run: {total_sent}")


if __name__ == "__main__":
    main()
