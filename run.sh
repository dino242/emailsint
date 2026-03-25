#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
RESET='\033[0m'

setup() {
    echo -e "${CYAN}  [*] Checking Python3...${RESET}"
    if ! command -v python3 &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip -qq
    fi
    echo -e "${CYAN}  [*] Installing packages...${RESET}"
    pip3 install -q aiohttp colorama dnspython python-whois 2>/dev/null || \
    pip3 install -q aiohttp colorama dnspython 2>/dev/null
    chmod +x emailsint.py proxy_server.py
    echo -e "${GREEN}  [✔] Ready!${RESET}"
    sleep 1
}

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
    echo -e "${CYAN}  ║       ${YELLOW}v3.0 — Email OSINT Tool${CYAN}                   ║${RESET}"
    echo -e "${CYAN}  ╚══════════════════════════════════════════════════╝${RESET}"
    echo ""
    echo -e "${WHITE}  40+ platforms · Gravatar OSINT · MX · WHOIS · Ngrok Proxy${RESET}"
    echo ""
}

show_menu() {
    echo -e "${WHITE}  ┌──────────────────────────────────────────────┐${RESET}"
    echo -e "${WHITE}  │                    MENU                      │${RESET}"
    echo -e "${WHITE}  ├──────────────────────────────────────────────┤${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[1]${WHITE} Quick scan                             │${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[2]${WHITE} Scan + HTML report                     │${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[3]${WHITE} Scan + JSON report                     │${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[4]${WHITE} Full scan  (HTML + JSON + verbose)     │${RESET}"
    echo -e "${WHITE}  │  ${YELLOW}[5]${WHITE} Start own ngrok proxy server           │${RESET}"
    echo -e "${WHITE}  │  ${YELLOW}[6]${WHITE} Scan using own ngrok proxy             │${RESET}"
    echo -e "${WHITE}  │  ${RED}[7]${WHITE} Exit                                   │${RESET}"
    echo -e "${WHITE}  └──────────────────────────────────────────────┘${RESET}"
    echo ""
}

ask_email() {
    echo -ne "${YELLOW}  ▶ Email address: ${RESET}"
    read -r EMAIL
    if [ -z "$EMAIL" ]; then
        echo -e "${RED}  [!] No email entered.${RESET}"
        sleep 1
        return 1
    fi
    return 0
}

pause() {
    echo ""
    echo -ne "${CYAN}  Press [Enter] to return to menu...${RESET}"
    read -r
}

option_1() {
    ask_email || return
    echo ""
    python3 emailsint.py "$EMAIL"
    pause
}

option_2() {
    ask_email || return
    echo -ne "${YELLOW}  ▶ HTML filename [report.html]: ${RESET}"
    read -r HTMLFILE
    HTMLFILE="${HTMLFILE:-report.html}"
    echo ""
    python3 emailsint.py "$EMAIL" --html "$HTMLFILE"
    echo -e "${GREEN}  [✔] Saved: ${HTMLFILE}${RESET}"
    echo -e "${CYAN}  [i] Cloud Shell: open Editor → click the file to preview${RESET}"
    pause
}

option_3() {
    ask_email || return
    echo -ne "${YELLOW}  ▶ JSON filename [report.json]: ${RESET}"
    read -r JSONFILE
    JSONFILE="${JSONFILE:-report.json}"
    echo ""
    python3 emailsint.py "$EMAIL" -o "$JSONFILE"
    echo -e "${GREEN}  [✔] Saved: ${JSONFILE}${RESET}"
    pause
}

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
    pause
}

option_5() {
    echo ""
    echo -e "${CYAN}  Starting ngrok proxy server...${RESET}"
    echo -e "${WHITE}  Get your free token at: https://dashboard.ngrok.com/get-started/your-authtoken${RESET}"
    echo -ne "${YELLOW}  ▶ ngrok authtoken: ${RESET}"
    read -r TOKEN
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}  [!] No token entered.${RESET}"
        pause
        return
    fi
    echo ""
    echo -e "${CYAN}  [*] Starting proxy server in background...${RESET}"
    NGROK_TOKEN="$TOKEN" python3 proxy_server.py &
    PROXY_PID=$!
    echo -e "${GREEN}  [✔] Proxy server started (PID: $PROXY_PID)${RESET}"
    echo -e "${CYAN}  [i] The ngrok URL will appear above. Copy it for option [6].${RESET}"
    echo -e "${YELLOW}  [i] Run 'kill $PROXY_PID' to stop the proxy server.${RESET}"
    pause
}

option_6() {
    echo ""
    echo -ne "${YELLOW}  ▶ Ngrok proxy URL (e.g. https://xxxx.ngrok-free.app): ${RESET}"
    read -r PURL
    if [ -z "$PURL" ]; then
        echo -e "${RED}  [!] No URL entered.${RESET}"
        pause
        return
    fi
    echo -ne "${YELLOW}  ▶ Auth token [Emaisint - dino242]: ${RESET}"
    read -r PAUTH
    PAUTH="${PAUTH:-emailsint2024}"
    ask_email || return
    echo -ne "${YELLOW}  ▶ HTML filename [report.html]: ${RESET}"
    read -r HTMLFILE
    HTMLFILE="${HTMLFILE:-report.html}"
    echo ""
    PROXY_URL="$PURL" PROXY_AUTH="$PAUTH" \
        python3 emailsint.py "$EMAIL" --html "$HTMLFILE" -v
    pause
}

setup

while true; do
    show_banner
    show_menu

    echo -ne "${WHITE}  ▶ Choose option [1-7]: ${RESET}"
    read -r CHOICE
    echo ""

    case $CHOICE in
        1) option_1 ;;
        2) option_2 ;;
        3) option_3 ;;
        4) option_4 ;;
        5) option_5 ;;
        6) option_6 ;;
        7)
            echo -e "${CYAN}  Goodbye!${RESET}"
            exit 0
            ;;
        *)
            echo -e "${RED}  [!] Invalid — choose 1-7.${RESET}"
            sleep 1
            ;;
    esac
done
