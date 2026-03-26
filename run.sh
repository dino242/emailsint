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
    if ! command -v python3 &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip -qq
    fi
    pip3 install -q aiohttp 2>/dev/null
    chmod +x proxy_server.py 2>/dev/null
}

show_banner() {
    clear
    echo ""
    echo -e "${CYAN}  ╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "${CYAN}  ║                                                  ║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE} ___ __  __   _   ___ _    ___ ___ _  _ _____${CYAN}   ║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE}| __|  \\/  | /_\\ |_ _| |  / __| __| \\| |_   _|${CYAN}  ║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE}| _|| |\\/| |/ _ \\ | || |__\\__ \\ _|| .\` | | |  ${CYAN}  ║${RESET}"
    echo -e "${CYAN}  ║  ${WHITE}|___|_|  |_/_/ \\_\\___|____|___/___|_|\\_| |_|  ${CYAN}  ║${RESET}"
    echo -e "${CYAN}  ║                                                  ║${RESET}"
    echo -e "${CYAN}  ║       ${YELLOW}v3.0 — Via localhost or Ngrok Dashboard${CYAN}      ║${RESET}"
    echo -e "${CYAN}  ╚══════════════════════════════════════════════════╝${RESET}"
    echo ""

    if [ -f "$PROXY_URL_FILE" ]; then
        URL=$(cat "$PROXY_URL_FILE" 2>/dev/null)
        if [ -n "$URL" ]; then
            echo -e "${GREEN}  ╔══════════════════════════════════════════════════╗${RESET}"
            echo -e "${GREEN}  ║  ✔  Proxy & Dashboard active                      ║${RESET}"
            echo -e "${GREEN}  ║  📊 ${WHITE}${URL}${GREEN}  ║${RESET}"
            echo -e "${GREEN}  ╚══════════════════════════════════════════════════╝${RESET}"
            echo ""
        fi
    fi
}

show_menu() {
    echo -e "${WHITE}  ┌──────────────────────────────────────────────┐${RESET}"
    echo -e "${WHITE}  │                    MENU                      │${RESET}"
    echo -e "${WHITE}  ├──────────────────────────────────────────────┤${RESET}"
    echo -e "${WHITE}  │  ${GREEN}[1]${WHITE} Set the Ngrok token and start server   │${RESET}"
    echo -e "${WHITE}  │  ${RED}[2]${WHITE} Stop the server                        │${RESET}"
    echo -e "${WHITE}  │  ${RED}[3]${WHITE} Exit                                  │${RESET}"
    echo -e "${WHITE}  └──────────────────────────────────────────────┘${RESET}"
    echo ""
}

pause() {
    echo ""
    echo -ne "${CYAN}  [Enter] zurück zum Menü...${RESET}"
    read -r
}

option_start() {
    # Stop old instance if running
    if [ -n "$PROXY_PID" ] && kill -0 "$PROXY_PID" 2>/dev/null; then
        kill "$PROXY_PID" 2>/dev/null
        pkill -f "ngrok" 2>/dev/null
        sleep 1
    fi
    rm -f "$PROXY_URL_FILE"

    echo ""
    echo -e "${CYAN}  ┌──────────────────────────────────────────────┐${RESET}"
    echo -e "${CYAN}  │  Input your ngrok authtoken                  │${RESET}"
    echo -e "${CYAN}  │  Get from: https://dashboard.ngrok.com/get-started      │${RESET}"
    echo -e "${CYAN}  └──────────────────────────────────────────────┘${RESET}"
    echo ""
    echo -ne "${YELLOW}  ▶ Ngrok Authtoken: ${RESET}"
    read -r TOKEN

    if [ -z "$TOKEN" ]; then
        echo -e "${RED}  [!] No token set - cancelling.${RESET}"
        pause
        return
    fi

    echo ""
    echo -e "${CYAN}  [*] Starte Webserver & ngrok...${RESET}"

    NGROK_TOKEN="$TOKEN" PROXY_URL_FILE="$PROXY_URL_FILE" \
        python3 proxy_server.py &
    PROXY_PID=$!

    echo -ne "${CYAN}  [*] Waiting for tunnel${RESET}"

    for i in $(seq 1 35); do
        sleep 1
        printf "${CYAN}.${RESET}"
        if [ -f "$PROXY_URL_FILE" ]; then
            URL=$(cat "$PROXY_URL_FILE" 2>/dev/null)
            if [ -n "$URL" ]; then
                echo ""
                echo ""
                echo -e "${GREEN}  ╔══════════════════════════════════════════════════╗${RESET}"
                echo -e "${GREEN}  ║                                                  ║${RESET}"
                echo -e "${GREEN}  ║  ✔  Tunnel activated URLs:   ║${RESET}"
                echo -e "${GREEN}  ║                                                  ║${RESET}"
                echo -e "${WHITE}  ║     ${URL}${GREEN}  ║${RESET}"
                echo -e "${GREEN}  ║                                                  ║${RESET}"
                echo -e "${GREEN}  ╚══════════════════════════════════════════════════╝${RESET}"
                echo ""
                echo -e "${CYAN}  → Link im Browser öffnen um Scan-Ergebnisse zu sehen!${RESET}"
                pause
                return
            fi
        fi
    done

    echo ""
    echo -e "${RED}  [!] Tunnel wasn't able to start.${RESET}"
    echo -e "${YELLOW}  [i] Token korrekt? → dashboard.ngrok.com${RESET}"
    pause
}

option_stop() {
    if [ -n "$PROXY_PID" ] && kill -0 "$PROXY_PID" 2>/dev/null; then
        kill "$PROXY_PID" 2>/dev/null
    fi
    pkill -f "proxy_server.py" 2>/dev/null
    pkill -f "ngrok" 2>/dev/null
    rm -f "$PROXY_URL_FILE"
    PROXY_PID=""
    echo -e "${GREEN}  [✔] Server & Tunnel gestoppt.${RESET}"
    sleep 1
}

# Bootstrap or sum shit
setup

while true; do
    show_banner
    show_menu

    echo -ne "${WHITE}  ▶ Option [1-3]: ${RESET}"
    read -r CHOICE
    echo ""

    case $CHOICE in
        1) option_start ;;
        2) option_stop  ;;
        3)
            [ -n "$PROXY_PID" ] && kill "$PROXY_PID" 2>/dev/null
            pkill -f "ngrok" 2>/dev/null
            rm -f "$PROXY_URL_FILE"
            echo -e "${CYAN}  Goodbye!${RESET}"
            exit 0
            ;;
        *)
            echo -e "${RED}  [!] Ungültige Eingabe — wähle 1, 2 oder 3.${RESET}"
            sleep 1
            ;;
    esac
done
