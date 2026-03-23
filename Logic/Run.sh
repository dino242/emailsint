#!/bin/bash
# ============================================================
#  emailsint — Alles-in-einem Script
#  Nach git clone einfach: bash run.sh deine@email.com
#  Proxies werden automatisch geladen — nichts nötig!
# ============================================================

set -e

EMAIL=$1
PROXIES=$2
HTML_OUT="${3:-report.html}"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║    emailsint v2.1 — Auto-Proxy Setup     ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

if [ -z "$EMAIL" ]; then
    echo "  Benutzung:"
    echo "    bash run.sh deine@email.com"
    echo "    bash run.sh deine@email.com proxies.txt     ← optional, eigene Proxies"
    echo ""
    exit 1
fi

# ── Python3 ───────────────────────────────────────────────
echo "  [1/3] Prüfe Python3..."
if ! command -v python3 &>/dev/null; then
    echo "  [*] Installiere Python3..."
    sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip -qq
fi
echo "  [✔] $(python3 --version)"

# ── Abhängigkeiten ────────────────────────────────────────
echo "  [2/3] Installiere Pakete..."
pip3 install -q -r requirements.txt
echo "  [✔] Pakete installiert"

# ── Starten ───────────────────────────────────────────────
echo "  [3/3] Starte Scan..."
echo ""
chmod +x emailsint.py

# Proxies: automatisch wenn keine Datei angegeben
ARGS="$EMAIL --html $HTML_OUT -v"
if [ -n "$PROXIES" ] && [ -f "$PROXIES" ]; then
    ARGS="$ARGS -p $PROXIES"
fi
# Ohne -p → Tool lädt automatisch Proxies

python3 emailsint.py $ARGS

if [ -f "$HTML_OUT" ]; then
    echo ""
    echo "  [✔] HTML-Report: $HTML_OUT"
    echo "  [i] In Google Cloud Shell: Klick auf Editor → $HTML_OUT öffnen"
fi
