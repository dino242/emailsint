# emailsint 🔍

> Finde heraus, auf welchen Plattformen deine E-Mail-Adresse registriert ist.  
> Reines Scraping — kein externer API-Dienst nötig.

---

## 🚀 Google Cloud Shell — Schnellstart

Öffne [shell.cloud.google.com](https://shell.cloud.google.com) und führe folgendes aus:

```bash
# 1. Repo klonen
git clone https://github.com/dino242/emailsint.git
cd emailsint

# 2. Starten — macht alles automatisch (Setup + Scan)
bash run.sh deine@email.com
```

**Fertig.** `run.sh` installiert alle Abhängigkeiten und startet den Scan sofort.

---

## 📋 Alle Benutzungsarten

```bash
# Einfacher Scan
bash run.sh deine@email.com

# Mit Proxy-Liste
bash run.sh deine@email.com proxies.txt

# Mit eigenem HTML-Report Namen
bash run.sh deine@email.com proxies.txt mein-report.html

# Nur das Python-Script direkt (nach erstem Setup)
python3 emailsint.py deine@email.com
python3 emailsint.py deine@email.com -v
python3 emailsint.py deine@email.com -p proxies.txt --html report.html -o report.json
```

---

## ⚙️ Alle Parameter (python3 emailsint.py)

| Parameter | Beschreibung | Standard |
|-----------|-------------|---------|
| `email` | Zu prüfende E-Mail (Pflicht) | — |
| `-p proxies.txt` | Proxy-Datei (eine pro Zeile) | kein |
| `-t 15` | Timeout pro Request (Sekunden) | 12 |
| `-o report.json` | JSON-Report speichern | kein |
| `--html report.html` | HTML-Report speichern | kein |
| `-v` | Auch nicht gefundene Plattformen zeigen | aus |

---

## 🔍 Was das Tool analysiert

### 1. E-Mail-Analyse
- **Anbieter erkennen** — Gmail, Outlook, ProtonMail, GMX, usw.
- **MX-Check** — Prüft ob die E-Mail-Domain erreichbar ist (DNS)
- **WHOIS** — Wann wurde die Domain registriert, welcher Registrar, welches Land

### 2. Plattform-Scan (30+ Seiten)

| Kategorie | Plattformen |
|-----------|------------|
| Tech | GitHub, GitLab, Gravatar |
| Social | Twitter/X, Tumblr, Pinterest, Reddit, Instagram, Snapchat, VK, Flickr |
| Professional | LinkedIn, Xing, Freelancer |
| Gaming | Twitch, Steam, Epic Games, Roblox |
| Music | Spotify, SoundCloud |
| Communication | Discord, Telegram |
| Cloud | Dropbox, Notion, Evernote |
| Finance | PayPal |
| Creative | Adobe, Behance, DeviantArt |
| Shopping | Etsy, eBay |

### 3. Benutzername scrapen
Wenn möglich wird der **Benutzername** direkt aus der Profilseite extrahiert (z.B. Gravatar).

### 4. HTML-Report
Übersichtlicher Report der gespeichert und im Browser geöffnet werden kann.

---

## 🔄 Proxy-Format

Erstelle eine Datei `proxies.txt`:

```
http://123.45.67.89:8080
http://user:passwort@98.76.54.32:3128
socks5://11.22.33.44:1080
```

---

## 📁 Dateien im Repo

```
emailsint/
├── emailsint.py      ← Hauptscript (Scan-Logik)
├── run.sh            ← Alles-in-einem: Setup + Start
├── requirements.txt  ← Python-Pakete
├── .gitignore
└── README.md
```

---

## ⚠️ Hinweis

Dieses Tool ist ausschließlich für die **eigene E-Mail-Adresse** gedacht, um eigene Accounts zu finden. Die Verwendung für fremde E-Mail-Adressen ohne Erlaubnis ist nicht gestattet.

---

## 📄 Lizenz

MIT
