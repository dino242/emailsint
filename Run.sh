#!/bin/bash
# ============================================================
#  emailsint — Interaktives Menü
#  Einfach: bash run.sh
# ============================================================

# ── Farben ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
WHITE='\033[1;37m'
RESET='\033[0m'

# ── Setup (einmalig) ──────────────────────────────────────
setup() {
    echo -e "${CYAN}  [*] Prüfe Abhängigkeiten...${RESET}"
    if ! command -v python3 &>/dev/null; then
        echo -e "${YELLOW}  [*] Installiere Python3...${RESET}"
        sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip -qq
    fi
    pip3 install -q -r requirements.txt
    chmod +x emailsint.py
    echo -e "${GREEN}  [✔] Bereit!${RESET}"
}

# ── Banner ────────────────────────────────────────────────
show_banner() {
    clear
    echo ""
    echo -e "${CYAN}  ╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "${CYAN}  ║                                                  ║${RESET}"
    echo -e "${CYAN}  ║   ${WHITE}___ __  __   _   ___ _    ___ ___ _  _ _____${CYAN}  ║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE}| __|  \/  | /_\ |_ _| |  / __| __| \| |_   _|${CYAN} ║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE}| _|| |\/| |/ _ \ | || |__\__ \ _|| .\` | | |  ${CYAN} ║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE}|___|_|  |_/_/ \_\___|____|___/___|_|\_| |_|  ${CYAN} ║${RESET}"
    echo -e "${CYAN}  ║                                                  ║${RESET}"
    echo -e "${CYAN}  ║      ${YELLOW}v2.1 — Email OSINT Tool${CYAN}                    ║${RESET}"
    echo -e "${CYAN}  ╚══════════════════════════════════════════════════╝${RESET}"
    echo ""
}

# ── Hauptmenü ─────────────────────────────────────────────
show_menu() {
    echo -e "${WHITE}  ┌─────────────────────────────────────┐${RESET}"
    echo -e "${WHITE}  │           HAUPTMENÜ                 │${RESET}"
    echo -e "${WHITE}  ├─────────────────────────────────────┤${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[1]${WHITE} Schnell-Scan (Auto-Proxies)      │${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[2]${WHITE} Scan mit eigener Proxy-Datei     │${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[3]${WHITE} Scan ohne Proxies                │${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[4]${WHITE} Scan + HTML-Report speichern     │${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[5]${WHITE} Vollständiger Scan (alles)       │${RESET}"
    echo -e "${WHITE}  │  ${RED}[6]${WHITE} Beenden                          │${RESET}"
    echo -e "${WHITE}  └─────────────────────────────────────┘${RESET}"
    echo ""
}

# ── E-Mail abfragen ───────────────────────────────────────
ask_email() {
    echo -ne "${YELLOW}  E-Mail-Adresse eingeben: ${RESET}"
    read EMAIL
    if [ -z "$EMAIL" ]; then
        echo -e "${RED}  [!] Keine E-Mail eingegeben.${RESET}"
        return 1
    fi
    echo ""
}

# ── Warten auf Enter ──────────────────────────────────────
pause() {
    echo ""
    echo -ne "${CYAN}  [Enter] drücken um zum Menü zurückzukehren...${RESET}"
    read
}

# ── Optionen 1: Schnell-Scan ──────────────────────────────
option_1() {
    ask_email || return
    echo -e "${CYAN}  [*] Starte Scan mit automatischen Proxies...${RESET}"
    echo ""
    python3 emailsint.py "$EMAIL" -v
    pause
}

# ── Option 2: Eigene Proxy-Datei ──────────────────────────
option_2() {
    ask_email || return
    echo -ne "${YELLOW}  Pfad zur Proxy-Datei (z.B. proxies.txt): ${RESET}"
    read PROXYFILE
    if [ ! -f "$PROXYFILE" ]; then
        echo -e "${RED}  [!] Datei nicht gefunden: $PROXYFILE${RESET}"
        pause
        return
    fi
    echo ""
    python3 emailsint.py "$EMAIL" -p "$PROXYFILE" -v
    pause
}

# ── Option 3: Ohne Proxies ────────────────────────────────
option_3() {
    ask_email || return
    echo -e "${CYAN}  [*] Starte Scan ohne Proxies...${RESET}"
    echo ""
    # Temporär Auto-Proxy deaktivieren via env-Variable
    NO_AUTO_PROXY=1 python3 emailsint.py "$EMAIL" -v
    pause
}

# ── Option 4: Mit HTML-Report ─────────────────────────────
option_4() {
    ask_email || return
    echo -ne "${YELLOW}  HTML-Report Dateiname [report.html]: ${RESET}"
    read HTMLFILE
    HTMLFILE="${HTMLFILE:-report.html}"
    echo ""
    python3 emailsint.py "$EMAIL" --html "$HTMLFILE" -v
    echo ""
    echo -e "${GREEN}  [✔] HTML-Report gespeichert: $HTMLFILE${RESET}"
    echo -e "${CYAN}  [i] In Google Cloud Shell: Editor öffnen → Datei ansehen${RESET}"
    pause
}

# ── Option 5: Vollständiger Scan ──────────────────────────
option_5() {
    ask_email || return
    echo -ne "${YELLOW}  HTML-Report Name [report.html]: ${RESET}"
    read HTMLFILE
    HTMLFILE="${HTMLFILE:-report.html}"
    echo -ne "${YELLOW}  JSON-Report Name [report.json]: ${RESET}"
    read JSONFILE
    JSONFILE="${JSONFILE:-report.json}"
    echo -ne "${YELLOW}  Proxy-Datei (leer = automatisch): ${RESET}"
    read PROXYFILE
    echo ""

    ARGS="$EMAIL --html $HTMLFILE -o $JSONFILE -v"
    if [ -n "$PROXYFILE" ] && [ -f "$PROXYFILE" ]; then
        ARGS="$ARGS -p $PROXYFILE"
    fi

    python3 emailsint.py $ARGS
    echo ""
    echo -e "${GREEN}  [✔] HTML: $HTMLFILE  |  JSON: $JSONFILE${RESET}"
    pause
}

# ── Hauptschleife ─────────────────────────────────────────
main() {
    setup

    while true; do
        show_banner
        show_menu

        echo -ne "${WHITE}  Wähle eine Option [1-6]: ${RESET}"
        read CHOICE
        echo ""

        case $CHOICE in
            1) option_1 ;;
            2) option_2 ;;
            3) option_3 ;;
            4) option_4 ;;
            5) option_5 ;;
            6)
                echo -e "${CYAN}  Auf Wiedersehen!${RESET}"
                echo ""
                exit 0
                ;;
            *)
                echo -e "${RED}  [!] Ungültige Eingabe — bitte 1-6 wählen.${RESET}"
                sleep 1
                ;;
        esac
    done
}

main
