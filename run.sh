#!/bin/bash
# ============================================================
#  emailsint v3.0 — Interactive Menu
#  Usage: bash run.sh
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
RESET='\033[0m'

# ── One-time setup ────────────────────────────────────────
setup() {
    echo -e "${CYAN}  [*] Checking Python3...${RESET}"
    if ! command -v python3 &>/dev/null; then
        echo -e "${YELLOW}  [*] Installing Python3...${RESET}"
        sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip -qq
    fi
    echo -e "${CYAN}  [*] Installing packages...${RESET}"
    pip3 install -q aiohttp colorama dnspython python-whois 2>/dev/null || \
    pip3 install -q aiohttp colorama dnspython 2>/dev/null
    chmod +x emailsint.py
    echo -e "${GREEN}  [✔] Ready!${RESET}"
    sleep 1
}

# ── Banner ────────────────────────────────────────────────
show_banner() {
    clear
    echo ""
    echo -e "${CYAN}  ╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "${CYAN}  ║                                                  ║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE} ___ __  __   _   ___ _    ___ ___ _  _ _____${CYAN} ║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE}| __|  \\/  | /_\\ |_ _| |  / __| __| \\| |_   _|${CYAN}║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE}| _|| |\\/| |/ _ \\ | || |__\\__ \\ _|| .\` | | |  ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE}|___|_|  |_/_/ \\_\\___|____|___/___|_|\\_| |_|  ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║                                                  ║${RESET}"
    echo -e "${CYAN}  ║       ${YELLOW}v3.0 — Made by - dino242${CYAN}                   ║${RESET}"
    echo -e "${CYAN}  ╚══════════════════════════════════════════════════╝${RESET}"
    echo ""
    echo -e "${WHITE}  Scans 40+ platforms · Auto proxies · MX · WHOIS · Gravatar${RESET}"
    echo ""
}

# ── Menu ──────────────────────────────────────────────────
show_menu() {
    echo -e "${WHITE}  ┌──────────────────────────────────────────┐${RESET}"
    echo -e "${WHITE}  │                  MENU                    │${RESET}"
    echo -e "${WHITE}  ├──────────────────────────────────────────┤${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[1]${WHITE} Quick scan                           │${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[2]${WHITE} Scan + save HTML report              │${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[3]${WHITE} Scan + save JSON report              │${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[4]${WHITE} Full scan (HTML + JSON + verbose)    │${RESET}"
    echo -e "${WHITE}  │  ${RED}[5]${WHITE} Exit                                 │${RESET}"
    echo -e "${WHITE}  └──────────────────────────────────────────┘${RESET}"
    echo ""
}

# ── Ask for email ─────────────────────────────────────────
ask_email() {
    echo -ne "${YELLOW}  ▶ Enter email address: ${RESET}"
    read -r EMAIL
    if [ -z "$EMAIL" ]; then
        echo -e "${RED}  [!] No email entered.${RESET}"
        sleep 1
        return 1
    fi
    return 0
}

# ── Pause ─────────────────────────────────────────────────
pause() {
    echo ""
    echo -ne "${CYAN}  Press [Enter] to return to menu...${RESET}"
    read -r
}

# ── Option 1: Quick scan ──────────────────────────────────
option_1() {
    ask_email || return
    echo ""
    python3 emailsint.py "$EMAIL"
    pause
}

# ── Option 2: Scan + HTML ─────────────────────────────────
option_2() {
    ask_email || return
    echo -ne "${YELLOW}  ▶ HTML filename [report.html]: ${RESET}"
    read -r HTMLFILE
    HTMLFILE="${HTMLFILE:-report.html}"
    echo ""
    python3 emailsint.py "$EMAIL" --html "$HTMLFILE"
    echo -e "${GREEN}  [✔] HTML report saved: ${HTMLFILE}${RESET}"
    echo -e "${CYAN}  [i] Google Cloud Shell: open Editor → click the file to view${RESET}"
    pause
}

# ── Option 3: Scan + JSON ─────────────────────────────────
option_3() {
    ask_email || return
    echo -ne "${YELLOW}  ▶ JSON filename [report.json]: ${RESET}"
    read -r JSONFILE
    JSONFILE="${JSONFILE:-report.json}"
    echo ""
    python3 emailsint.py "$EMAIL" -o "$JSONFILE"
    echo -e "${GREEN}  [✔] JSON report saved: ${JSONFILE}${RESET}"
    pause
}

# ── Option 4: Full scan ───────────────────────────────────
option_4() {
    ask_email || return
    echo -ne "${YELLOW}  ▶ HTML filename [report.html]: ${RESET}"
    read -r HTMLFILE
    HTMLFILE="${HTMLFILE:-report.html}"
    echo -ne "${YELLOW}  ▶ JSON filename [report.json]: ${RESET}"
    read -r JSONFILE
    JSONFILE="${JSONFILE:-report.json}"
    echo ""
    python3 emailsint.py "$EMAIL" --html "$HTMLFILE" -o "$JSONFILE" -v
    echo -e "${GREEN}  [✔] HTML: ${HTMLFILE}   JSON: ${JSONFILE}${RESET}"
    pause
}

# ── Main loop ─────────────────────────────────────────────
setup

while true; do
    show_banner
    show_menu

    echo -ne "${WHITE}  ▶ Choose option [1-5]: ${RESET}"
    read -r CHOICE
    echo ""

    case $CHOICE in
        1) option_1 ;;
        2) option_2 ;;
        3) option_3 ;;
        4) option_4 ;;
        5)
            echo -e "${CYAN}  Goodbye!${RESET}"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}  [!] Invalid input — please choose 1-5.${RESET}"
            sleep 1
            ;;
    esac
done
