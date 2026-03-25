# emailsint 🔍

> Find which platforms are registered with your email address.  
> Pure scraping — no API keys needed. **88 platforms** checked.

---

## ⚡ One-Line Install & Run

```bash
git clone https://github.com/dino242/emailsint.git && cd emailsint && bash run.sh
```

---

## 📁 File Structure

```
emailsint/
├── emailsint.py       ← Main entry point
├── platforms.py       ← All 88 platform definitions
├── osint.py           ← MX, WHOIS, Gravatar, provider detection
├── scanner.py         ← Async scanner + ngrok routing
├── proxy_manager.py   ← Auto proxy fetch, test, ngrok integration
├── proxy_server.py    ← Your own ngrok proxy server
├── report.py          ← HTML + JSON report generation
├── run.sh             ← Interactive menu
└── requirements.txt
```

---

## 🖥️ Menu

```
[1] Quick scan
[2] Scan + HTML report
[3] Scan + JSON report
[4] Full scan  (HTML + JSON + verbose)
[5] Start own ngrok proxy server
[6] Scan using own ngrok proxy
[7] Exit
```

---

## 🌐 Platforms (88 total)

| Category | Platforms |
|----------|-----------|
| **Social** (16) | Facebook, Twitter/X, Instagram, TikTok, Snapchat, Pinterest, Reddit, Tumblr, VK, Flickr, Foursquare, Quora, Meetup, Mastodon, Minds, MeWe |
| **Gaming** (11) | Twitch, Steam, Epic Games, Roblox, Ubisoft, EA/Origin, Battle.net, PlayStation, Xbox/Microsoft, Minecraft, GOG |
| **Tech** (8) | GitHub, GitLab, Gravatar, Codecademy, HackerNews, Stack Overflow, Bitbucket, npm |
| **Communication** (7) | Discord, Skype, Zoom, Slack, Telegram, Signal, Teams |
| **Music** (6) | Spotify, SoundCloud, Last.fm, Deezer, Apple Music, Bandcamp |
| **Creative** (6) | Adobe, Behance, DeviantArt, Canva, 500px, Figma |
| **Cloud** (5) | Dropbox, Google Drive, OneDrive, iCloud, Box |
| **Finance** (5) | PayPal, Coinbase, Binance, Kraken, Revolut |
| **Productivity** (5) | Notion, Evernote, Trello, Asana, Monday.com |
| **Professional** (5) | LinkedIn, Xing, Freelancer, Upwork, Fiverr |
| **Video** (4) | YouTube, Vimeo, Dailymotion, Twitch |
| **Shopping** (4) | Etsy, eBay, Amazon, Shopify |
| **Streaming** (3) | Netflix, Hulu, Disney+ |
| **Travel** (3) | Airbnb, Booking.com, Uber |

---

## 🔎 OSINT Features

| Feature | Details |
|---------|---------|
| **Provider** | Gmail, Outlook, ProtonMail, GMX, iCloud, 20+ more |
| **MX Record** | DNS check — can the domain receive email? |
| **WHOIS** | Domain creation date, registrar, country |
| **Gravatar** | Name, username, location, bio, linked accounts, URLs, avatar |

---

## 🔄 Proxy Modes

| Mode | How |
|------|-----|
| **Own ngrok proxy** | Menu `[5]` to start server, `[6]` to scan through it |
| **Manual file** | `-p proxies.txt` (one proxy per line) |
| **Auto** | Fetched + tested from public lists automatically |

### Own ngrok proxy setup
1. Free token at [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken)
2. Menu `[5]` → enter token → server starts
3. Copy the ngrok URL
4. Menu `[6]` → paste URL → scan

---

## ⚙️ Manual usage

```bash
python3 emailsint.py your@email.com
python3 emailsint.py your@email.com --html report.html -o report.json -v
python3 emailsint.py your@email.com -p proxies.txt

PROXY_URL=https://xxxx.ngrok-free.app PROXY_AUTH=emailsint2024 \
  python3 emailsint.py your@email.com --html report.html
```

---

## ⚠️ Legal

For your own email address only.

## 📄 License

MIT
