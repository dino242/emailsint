# emailsint 🔍

> Find which platforms are registered with your email address.  
> Pure scraping — no API keys needed. 40+ platforms checked.

---

## ⚡ One-Line Install & Run

```bash
git clone https://github.com/dino242/emailsint.git && cd emailsint && bash Run.sh
```

That's it. The menu will appear automatically.

---

## 📋 What it does

### 🔎 Email Analysis
| Check | Details |
|-------|---------|
| **Provider** | Detects Gmail, Outlook, ProtonMail, GMX, iCloud, etc. |
| **MX Record** | Verifies the domain can receive email (DNS lookup) |
| **WHOIS** | Domain creation date, registrar, country |

### 👤 Gravatar OSINT
Fetches the full Gravatar profile linked to the email hash:
- Display name & username
- Location & bio
- Linked external accounts (Twitter, LinkedIn, etc.)
- Personal URLs
- Avatar image

### 🌐 Platform Scan (40+ sites)

| Category | Platforms |
|----------|-----------|
| Tech | GitHub, GitLab, Gravatar, Codecademy, HackerNews |
| Social | Twitter/X, Instagram, Reddit, Tumblr, Pinterest, Snapchat, VK, Flickr, Foursquare, Quora, Meetup |
| Professional | LinkedIn, Xing, Freelancer, Upwork |
| Gaming | Twitch, Steam, Epic Games, Roblox, Ubisoft, EA/Origin |
| Music | Spotify, SoundCloud, Last.fm, Deezer |
| Communication | Discord, Skype, Zoom, Slack |
| Cloud | Dropbox, Notion, Evernote, Trello |
| Finance | PayPal, Coinbase, Binance |
| Creative | Adobe, Behance, DeviantArt, Canva, 500px |
| Shopping | Etsy, eBay, Amazon |

### 📊 Reports
- **HTML report** — visual dark-theme dashboard with Gravatar profile
- **JSON report** — full machine-readable output

### 🔄 Auto Proxies
Automatically fetches and tests free proxies from public lists. Falls back gracefully if none work — no manual setup needed.

---

## 🖥️ Google Cloud Shell — Usage

```bash
# Clone and start
git clone https://github.com/dino242/emailsint.git && cd emailsint && bash run.sh
```

**Menu options:**
```
[1] Quick scan
[2] Scan + save HTML report
[3] Scan + save JSON report
[4] Full scan (HTML + JSON + verbose)
[5] Exit
```

> **HTML reports** — In Google Cloud Shell, open the **Editor** tab and click the `.html` file to preview it in your browser.

---

## ⚙️ Manual usage (after first run)

```bash
# Basic
python3 emailsint.py your@email.com

# With HTML + JSON reports
python3 emailsint.py your@email.com --html report.html -o report.json

# Verbose (shows not-found platforms too)
python3 emailsint.py your@email.com -v

# With your own proxy file
python3 emailsint.py your@email.com -p proxies.txt
```

| Argument | Description | Default |
|----------|-------------|---------|
| `email` | Email to scan (required) | — |
| `-p file` | Proxy list file (one per line) | auto |
| `-t 15` | Request timeout in seconds | 12 |
| `-o file.json` | Save JSON report | — |
| `--html file.html` | Save HTML report | — |
| `-v` | Verbose output | off |

---

## 📁 Repo structure

```
emailsint/
├── emailsint.py      ← Main script (all scan logic)
├── run.sh            ← Auto-setup + interactive menu
├── requirements.txt  ← Python dependencies
├── .gitignore
└── README.md
```

---

## ⚠️ Legal notice

This tool is intended **only for scanning your own email address** to find your own registered accounts. Do not use it on email addresses that are not yours.

---

## 📄 License

MIT
