#!/bin/bash

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}   Multi-Agent Development System     ${NC}"
echo -e "${GREEN}=======================================${NC}"

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment... (puede tardar unos minutos)${NC}"
    python3 -m venv venv || { echo -e "${RED}Error creando entorno virtual.${NC}"; exit 1; }
    echo -e "${GREEN}Entorno virtual creado. Activando...${NC}"
    source venv/bin/activate || { echo -e "${RED}Error activando entorno virtual.${NC}"; exit 1; }
    echo -e "${YELLOW}Instalando dependencias... (puede tardar varios minutos)${NC}"
    pip install -r requirements.txt || { echo -e "${RED}Error instalando dependencias.${NC}"; exit 1; }
else
    echo -e "${GREEN}Entorno virtual encontrado. Activando...${NC}"
    source venv/bin/activate || { echo -e "${RED}Error activando entorno virtual.${NC}"; exit 1; }
fi

echo -e "${GREEN}Entorno virtual activado correctamente.${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from example...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${RED}Please edit the .env file to add your OpenAI API key.${NC}"
        exit 1
    else
        echo -e "${RED}Error: .env.example file not found.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Archivo .env encontrado.${NC}"

# Check if OpenAI API key is set correctly
if ! grep -q "OPENAI_API_KEY=" .env || grep -q "OPENAI_API_KEY=$" .env; then
    echo -e "${RED}Error: OPENAI_API_KEY is not set in .env file.${NC}"
    echo -e "${RED}Please edit the .env file to add your OpenAI API key.${NC}"
    exit 1
fi

echo -e "${GREEN}OpenAI API Key configurada correctamente.${NC}"

# Check if there's a typo in the environment variable name (common error)
if grep -q "OPENAI_API_EKY" .env; then
    echo -e "${RED}Error: Found 'OPENAI_API_EKY' in .env file which is a typo.${NC}"
    echo -e "${RED}Please change it to 'OPENAI_API_KEY' (note the K and E order).${NC}"
    exit 1
fi

# Function to check if a port is in use
is_port_in_use() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

echo -e "${YELLOW}Comprobando puertos...${NC}"
# Check if ports are in use
for port in 5001 5002 5003; do
    if is_port_in_use $port; then
        echo -e "${RED}Port $port is already in use. Please close the application using it.${NC}"
        exit 1
    fi
done
echo -e "${GREEN}Puertos disponibles.${NC}"

# Function to handle cleanup when the script is terminated
cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"
    if [ ! -z "$PLANNER_PID" ]; then
        kill $PLANNER_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    exit 0
}

# Set up trap for cleanup
trap cleanup INT TERM

# Display menu
echo -e "${CYAN}Select which agents to run:${NC}"
echo "1) All agents (Planner, Frontend, Backend)"
echo "2) Planner agent only"
echo "3) Frontend agent only"
echo "4) Backend agent only"
echo "5) Frontend and Backend agents"
echo -e "${CYAN}Enter your choice (1-5):${NC}"
read choice

case $choice in
    1)
        # Start all agents
        echo -e "${GREEN}Starting all agents...${NC}"

        echo -e "${BLUE}Starting Planner Agent server...${NC}"
        python agents/planner/server.py &
        PLANNER_PID=$!
        sleep 2

        echo -e "${BLUE}Starting Frontend Agent server...${NC}"
        python agents/frontend/server.py &
        FRONTEND_PID=$!
        sleep 2

        echo -e "${BLUE}Starting Backend Agent server...${NC}"
        python agents/backend/server.py &
        BACKEND_PID=$!
        sleep 2

        echo -e "${GREEN}All agent servers are running!${NC}"
        echo -e "${PURPLE}Now running Planner Agent client...${NC}"
        python agents/planner/client.py

        echo -e "\n${YELLOW}Planner has created the project plan and tasks!${NC}"
        echo -e "${CYAN}Would you like to continue with development? (y/n)${NC}"
        read continue_dev

        if [[ $continue_dev == "y" || $continue_dev == "Y" ]]; then
            # Ask for project path
            echo -e "${CYAN}Enter the path to your project (or leave empty to use the current directory):${NC}"
            read project_path

            # Use current directory if no path is provided
            if [ -z "$project_path" ]; then
                project_path=$(pwd)
            fi

            # Start frontend and backend clients in separate terminals if possible
            if command -v gnome-terminal &> /dev/null; then
                gnome-terminal -- bash -c "cd $(pwd) && source venv/bin/activate && python agents/frontend/client.py \"$project_path\"; exec bash"
                gnome-terminal -- bash -c "cd $(pwd) && source venv/bin/activate && python agents/backend/client.py \"$project_path\"; exec bash"
            elif command -v xterm &> /dev/null; then
                xterm -e "cd $(pwd) && source venv/bin/activate && python agents/frontend/client.py \"$project_path\"" &
                xterm -e "cd $(pwd) && source venv/bin/activate && python agents/backend/client.py \"$project_path\"" &
            else
                echo -e "${YELLOW}Cannot open new terminals automatically.${NC}"
                echo -e "${YELLOW}Please run these commands in separate terminals:${NC}"
                echo -e "${CYAN}python agents/frontend/client.py \"$project_path\"${NC}"
                echo -e "${CYAN}python agents/backend/client.py \"$project_path\"${NC}"
            fi
        fi
        ;;
    2)
        # Start Planner agent only
        echo -e "${BLUE}Starting Planner Agent server...${NC}"
        python agents/planner/server.py &
        PLANNER_PID=$!
        sleep 2

        echo -e "${PURPLE}Now running Planner Agent client...${NC}"
        python agents/planner/client.py
        ;;
    3)
        # Start Frontend agent only
        echo -e "${BLUE}Starting Frontend Agent server...${NC}"
        python agents/frontend/server.py &
        FRONTEND_PID=$!
        sleep 2

        echo -e "${CYAN}Enter the path to your project (or leave empty to use the current directory):${NC}"
        read project_path

        # Use current directory if no path is provided
        if [ -z "$project_path" ]; then
            project_path=$(pwd)
        fi

        echo -e "${PURPLE}Now running Frontend Agent client...${NC}"
        python agents/frontend/client.py "$project_path"
        ;;
    4)
        # Start Backend agent only
        echo -e "${BLUE}Starting Backend Agent server...${NC}"
        python agents/backend/server.py &
        BACKEND_PID=$!
        sleep 2

        echo -e "${CYAN}Enter the path to your project (or leave empty to use the current directory):${NC}"
        read project_path

        # Use current directory if no path is provided
        if [ -z "$project_path" ]; then
            project_path=$(pwd)
        fi

        echo -e "${PURPLE}Now running Backend Agent client...${NC}"
        python agents/backend/client.py "$project_path"
        ;;
    5)
        # Start Frontend and Backend agents
        echo -e "${BLUE}Starting Frontend Agent server...${NC}"
        python agents/frontend/server.py &
        FRONTEND_PID=$!
        sleep 2

        echo -e "${BLUE}Starting Backend Agent server...${NC}"
        python agents/backend/server.py &
        BACKEND_PID=$!
        sleep 2

        # Ask for project path
        echo -e "${CYAN}Enter the path to your project (or leave empty to use the current directory):${NC}"
        read project_path

        # Use current directory if no path is provided
        if [ -z "$project_path" ]; then
            project_path=$(pwd)
        fi

        # Start frontend and backend clients in separate terminals if possible
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "cd $(pwd) && source venv/bin/activate && python agents/frontend/client.py \"$project_path\"; exec bash"
            gnome-terminal -- bash -c "cd $(pwd) && source venv/bin/activate && python agents/backend/client.py \"$project_path\"; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -e "cd $(pwd) && source venv/bin/activate && python agents/frontend/client.py \"$project_path\"" &
            xterm -e "cd $(pwd) && source venv/bin/activate && python agents/backend/client.py \"$project_path\"" &
        else
            echo -e "${YELLOW}Cannot open new terminals automatically.${NC}"
            echo -e "${YELLOW}Please run these commands in separate terminals:${NC}"
            echo -e "${CYAN}python agents/frontend/client.py \"$project_path\"${NC}"
            echo -e "${CYAN}python agents/backend/client.py \"$project_path\"${NC}"
        fi
        ;;
    *)
        echo -e "${RED}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

# Wait for all background processes
wait
