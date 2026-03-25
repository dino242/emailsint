#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
RESET='\033[0m'

PROXY_PID=""
PROXY_URL_FILE="/tmp/emailsint_proxy_url"

setup() {
    echo -e "${CYAN}  [*] Checking Python3...${RESET}"
    if ! command -v python3 &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip -qq
    fi
    echo -e "${CYAN}  [*] Installing packages...${RESET}"
    pip3 install -q aiohttp colorama dnspython python-whois 2>/dev/null || \
    pip3 install -q aiohttp colorama dnspython 2>/dev/null
    chmod +x emailsint.py proxy_server.py 2>/dev/null
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

    # Show proxy status in banner if running
    if [ -f "$PROXY_URL_FILE" ]; then
        SAVED_URL=$(cat "$PROXY_URL_FILE" 2>/dev/null)
        if [ -n "$SAVED_URL" ]; then
            echo -e "${GREEN}  ✔ Proxy aktiv: ${WHITE}${SAVED_URL}${RESET}"
            echo -e "${GREEN}  ✔ Dashboard:   ${WHITE}${SAVED_URL}${RESET}"
            echo ""
        fi
    fi

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
    echo -e "${WHITE}  │  ${YELLOW}[5]${WHITE} Proxy starten + Dashboard              │${RESET}"
    echo -e "${WHITE}  │  ${YELLOW}[6]${WHITE} Scan via Proxy (mit Dashboard)         │${RESET}"
    echo -e "${WHITE}  │  ${RED}[7]${WHITE} Proxy stoppen                          │${RESET}"
    echo -e "${WHITE}  │  ${RED}[8]${WHITE} Exit                                   │${RESET}"
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

get_proxy_url() {
    if [ -f "$PROXY_URL_FILE" ]; then
        cat "$PROXY_URL_FILE" 2>/dev/null
    fi
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
    # Stop old proxy if running
    if [ -n "$PROXY_PID" ] && kill -0 "$PROXY_PID" 2>/dev/null; then
        echo -e "${YELLOW}  [*] Stoppe alten Proxy (PID: $PROXY_PID)...${RESET}"
        kill "$PROXY_PID" 2>/dev/null
        pkill -f "ngrok" 2>/dev/null
        sleep 1
    fi
    rm -f "$PROXY_URL_FILE"

    echo ""
    echo -e "${CYAN}  ┌─────────────────────────────────────────────┐${RESET}"
    echo -e "${CYAN}  │  Ngrok Proxy + Dashboard Setup               │${RESET}"
    echo -e "${CYAN}  │  Token holen: dashboard.ngrok.com            │${RESET}"
    echo -e "${CYAN}  └─────────────────────────────────────────────┘${RESET}"
    echo ""
    echo -ne "${YELLOW}  ▶ Ngrok Authtoken: ${RESET}"
    read -r TOKEN
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}  [!] Kein Token eingegeben.${RESET}"
        pause
        return
    fi

    echo ""
    echo -e "${CYAN}  [*] Starte Proxy-Server im Hintergrund...${RESET}"

    # Start proxy_server.py — it handles ngrok itself and writes URL to file
    NGROK_TOKEN="$TOKEN" PROXY_URL_FILE="$PROXY_URL_FILE" \
        python3 proxy_server.py &
    PROXY_PID=$!

    echo -e "${CYAN}  [*] Warte auf ngrok-Tunnel${RESET}"

    # Wait up to 30s for proxy_server.py to write the URL
    for i in $(seq 1 30); do
        sleep 1
        printf "${CYAN}.${RESET}"
        if [ -f "$PROXY_URL_FILE" ]; then
            URL=$(cat "$PROXY_URL_FILE")
            if [ -n "$URL" ]; then
                echo ""
                echo ""
                echo -e "${GREEN}  ╔══════════════════════════════════════════════╗${RESET}"
                echo -e "${GREEN}  ║  ✔  ngrok Tunnel aktiv!                     ║${RESET}"
                echo -e "${GREEN}  ║                                              ║${RESET}"
                echo -e "${GREEN}  ║  📊 Dashboard: ${WHITE}${URL}${GREEN}  ║${RESET}"
                echo -e "${GREEN}  ║  🔑 Auth:      ${WHITE}emailsint2024${GREEN}             ║${RESET}"
                echo -e "${GREEN}  ║  🔌 PID:       ${WHITE}${PROXY_PID}${GREEN}                          ║${RESET}"
                echo -e "${GREEN}  ╚══════════════════════════════════════════════╝${RESET}"
                echo ""
                echo -e "${CYAN}  → Öffne den Link im Browser um Scan-Ergebnisse zu sehen!${RESET}"
                pause
                return
            fi
        fi
    done

    echo ""
    echo -e "${RED}  [!] ngrok Tunnel konnte nicht gestartet werden.${RESET}"
    echo -e "${YELLOW}  [i] Token korrekt? Prüfe: dashboard.ngrok.com${RESET}"
    pause
}

option_6() {
    PURL=$(get_proxy_url)

    if [ -z "$PURL" ]; then
        echo ""
        echo -e "${YELLOW}  [!] Kein aktiver Proxy gefunden.${RESET}"
        echo -e "${CYAN}  [i] Starte zuerst den Proxy mit Option [5].${RESET}"
        echo ""
        echo -ne "${YELLOW}  Oder manuelle URL eingeben (leer = Abbrechen): ${RESET}"
        read -r PURL
        if [ -z "$PURL" ]; then
            pause
            return
        fi
    else
        echo ""
        echo -e "${GREEN}  [✔] Nutze aktiven Proxy: ${WHITE}${PURL}${RESET}"
    fi

    ask_email || return

    echo -ne "${YELLOW}  ▶ HTML filename [report.html]: ${RESET}"
    read -r HTMLFILE
    HTMLFILE="${HTMLFILE:-report.html}"

    echo ""
    PROXY_URL="$PURL" PROXY_AUTH="emailsint2024" \
        python3 emailsint.py "$EMAIL" --html "$HTMLFILE" -v

    echo ""
    echo -e "${GREEN}  [✔] Scan fertig! Ergebnisse live auf:${RESET}"
    echo -e "${WHITE}  → ${PURL}${RESET}"
    pause
}

option_7() {
    if [ -n "$PROXY_PID" ] && kill -0 "$PROXY_PID" 2>/dev/null; then
        kill "$PROXY_PID" 2>/dev/null
        pkill -f "ngrok" 2>/dev/null
        rm -f "$PROXY_URL_FILE"
        PROXY_PID=""
        echo -e "${GREEN}  [✔] Proxy gestoppt.${RESET}"
    else
        pkill -f "proxy_server.py" 2>/dev/null
        pkill -f "ngrok" 2>/dev/null
        rm -f "$PROXY_URL_FILE"
        PROXY_PID=""
        echo -e "${YELLOW}  [i] Kein aktiver Proxy gefunden (oder bereits gestoppt).${RESET}"
    fi
    sleep 1
}

setup

while true; do
    show_banner
    show_menu

    echo -ne "${WHITE}  ▶ Choose option [1-8]: ${RESET}"
    read -r CHOICE
    echo ""

    case $CHOICE in
        1) option_1 ;;
        2) option_2 ;;
        3) option_3 ;;
        4) option_4 ;;
        5) option_5 ;;
        6) option_6 ;;
        7) option_7 ;;
        8)
            # Clean up on exit
            if [ -n "$PROXY_PID" ]; then
                kill "$PROXY_PID" 2>/dev/null
                pkill -f "ngrok" 2>/dev/null
            fi
            rm -f "$PROXY_URL_FILE"
            echo -e "${CYAN}  Goodbye!${RESET}"
            exit 0
            ;;
        *)
            echo -e "${RED}  [!] Invalid — choose 1-8.${RESET}"
            sleep 1
            ;;
    esac
done
