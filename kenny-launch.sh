#!/bin/bash

# Kenny v2.0 - One-Click Launcher
# Local-first multi-agent personal assistant system
# Usage: ./kenny-launch.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KENNY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$KENNY_ROOT/logs"
PID_DIR="$KENNY_ROOT/pids"

# Service ports
AGENT_REGISTRY_PORT=8001
COORDINATOR_PORT=8002
GATEWAY_PORT=9000
DASHBOARD_PORT=3001
BRIDGE_PORT=5100
MAIL_AGENT_PORT=8000
CONTACTS_AGENT_PORT=8003
MEMORY_AGENT_PORT=8004
WHATSAPP_AGENT_PORT=8005
IMESSAGE_AGENT_PORT=8006
CALENDAR_AGENT_PORT=8007

# Create directories
mkdir -p "$LOG_DIR" "$PID_DIR"

# Cleanup function
cleanup() {
    printf "${YELLOW}Kenny is shutting down...${NC}\n"
    ./kenny-stop.sh 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Utility functions
log() {
    printf "${GREEN}[$(date +'%H:%M:%S')] %s${NC}\n" "$1"
}

warn() {
    printf "${YELLOW}[$(date +'%H:%M:%S')] WARNING: %s${NC}\n" "$1"
}

error() {
    printf "${RED}[$(date +'%H:%M:%S')] ERROR: %s${NC}\n" "$1"
}

info() {
    printf "${BLUE}[$(date +'%H:%M:%S')] %s${NC}\n" "$1"
}

# Check if port is available
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        error "Port $port is already in use (needed for $service)"
        echo "Please free port $port and try again, or run './kenny-stop.sh' if Kenny is already running"
        return 1
    fi
    return 0
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_wait=${3:-30}
    local count=0
    
    info "Waiting for $service_name to be ready..."
    while [ $count -lt $max_wait ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            log "$service_name is ready!"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        printf "."
    done
    echo
    error "$service_name failed to start after ${max_wait} seconds"
    return 1
}

# Start a service in the background
start_service() {
    local service_name=$1
    local start_command=$2
    local working_directory=$3
    local log_file="$LOG_DIR/${service_name}.log"
    local pid_file="$PID_DIR/${service_name}.pid"
    
    info "Starting $service_name..."
    
    # Change to service directory
    cd "$working_directory"
    
    # Start the service and capture PID
    eval "$start_command" > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"
    
    log "$service_name started with PID $pid"
    
    # Return to Kenny root
    cd "$KENNY_ROOT"
}

# Check if service is running
check_service() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            return 0  # Running
        else
            rm -f "$pid_file"
            return 1  # Not running
        fi
    fi
    return 1  # No PID file
}

# Display banner
printf "${BLUE}"
cat << "EOF"
 _  __                         ____  
| |/ /__ _ __  _ __  _   _     |___ \ 
| ' // _ \ '_ \| '_ \| | | |     __) |
| . \  __/ | | | | | | |_| |   / __/ 
|_|\_\___|_| |_|_| |_|\__, |  |_____|
                     |___/          
Local-First Multi-Agent Personal Assistant
EOF
printf "${NC}\n"

info "Kenny v2.0 Launch Process Starting..."
info "Kenny Root Directory: $KENNY_ROOT"

# Phase 1: Prerequisites Check
printf "\n${BLUE}=== Phase 1: Prerequisites Check ===${NC}\n"

# Check if we're in the right directory
if [ ! -f "$KENNY_ROOT/PROJECT_STATUS.md" ]; then
    error "Cannot find PROJECT_STATUS.md. Please run this script from the Kenny v2 root directory."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    error "Python 3 is required but not installed"
    exit 1
fi
log "Python 3: $(python3 --version)"

# Check Node.js/npm
if ! command -v npm &> /dev/null; then
    error "Node.js/npm is required but not installed"
    exit 1
fi
log "Node.js: $(node --version)"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    warn "Ollama not found. Kenny will work with limited functionality."
    warn "Install with: brew install ollama"
else
    log "Ollama: $(ollama --version | head -n1)"
    # Check if Ollama service is running
    if ! pgrep -f "ollama serve" > /dev/null; then
        info "Starting Ollama service..."
        ollama serve &
        sleep 3
    fi
fi

# Check Docker (optional)
if command -v docker &> /dev/null; then
    log "Docker: $(docker --version | head -n1)"
else
    warn "Docker not found (optional for some features)"
fi

# Check port availability
printf "\n${BLUE}=== Phase 2: Port Availability Check ===${NC}\n"
check_port $AGENT_REGISTRY_PORT "Agent Registry" || exit 1
check_port $COORDINATOR_PORT "Coordinator" || exit 1  
check_port $GATEWAY_PORT "Gateway" || exit 1
check_port $DASHBOARD_PORT "Dashboard" || exit 1
check_port $BRIDGE_PORT "Bridge" || exit 1
check_port $MAIL_AGENT_PORT "Mail Agent" || exit 1
check_port $CONTACTS_AGENT_PORT "Contacts Agent" || exit 1
check_port $MEMORY_AGENT_PORT "Memory Agent" || exit 1
check_port $WHATSAPP_AGENT_PORT "WhatsApp Agent" || exit 1
check_port $IMESSAGE_AGENT_PORT "iMessage Agent" || exit 1
check_port $CALENDAR_AGENT_PORT "Calendar Agent" || exit 1

log "All required ports are available"

# Phase 3: Agent SDK Installation
printf "\n${BLUE}=== Phase 3: Agent SDK Setup ===${NC}\n"
if [ -d "$KENNY_ROOT/services/agent-sdk" ]; then
    cd "$KENNY_ROOT/services/agent-sdk"
    if [ ! -f "kenny_agent_sdk.egg-info/PKG-INFO" ]; then
        info "Installing Agent SDK..."
        pip3 install -e . >> "$LOG_DIR/agent-sdk-install.log" 2>&1
        log "Agent SDK installed successfully"
    else
        log "Agent SDK already installed"
    fi
    cd "$KENNY_ROOT"
else
    warn "Agent SDK directory not found"
fi

# Phase 4: Dashboard Dependencies
printf "\n${BLUE}=== Phase 4: Dashboard Dependencies ===${NC}\n"
if [ -d "$KENNY_ROOT/services/dashboard" ]; then
    cd "$KENNY_ROOT/services/dashboard"
    if [ ! -d "node_modules" ]; then
        info "Installing dashboard dependencies..."
        npm install >> "$LOG_DIR/dashboard-install.log" 2>&1
        log "Dashboard dependencies installed"
    else
        log "Dashboard dependencies already installed"
    fi
    cd "$KENNY_ROOT"
fi

# Phase 5: Service Startup
printf "\n${BLUE}=== Phase 5: Starting Core Services ===${NC}\n"

# Step 1: Start Agent Registry (foundational service)
start_service "agent-registry" \
    "python3 -m uvicorn src.main:app --host 0.0.0.0 --port $AGENT_REGISTRY_PORT" \
    "$KENNY_ROOT/services/agent-registry"

# Wait for registry to be ready
wait_for_service "http://localhost:$AGENT_REGISTRY_PORT/health" "Agent Registry" || exit 1

# Step 2: Start Coordinator (depends on registry)  
start_service "coordinator" \
    "python3 -m src.main --port $COORDINATOR_PORT" \
    "$KENNY_ROOT/services/coordinator"

# Wait for coordinator to be ready
wait_for_service "http://localhost:$COORDINATOR_PORT/health" "Coordinator" || exit 1

# Step 3: Start Gateway (depends on registry and coordinator)
start_service "gateway" \
    "python3 -m src.main --port $GATEWAY_PORT" \
    "$KENNY_ROOT/services/gateway"

# Wait for gateway to be ready  
wait_for_service "http://localhost:$GATEWAY_PORT/health" "Gateway" || exit 1

# Phase 6: Start Agents
printf "\n${BLUE}=== Phase 6: Starting Agents ===${NC}\n"

# Start Bridge (needed for live data)
start_service "bridge" \
    "MAIL_BRIDGE_MODE=live IMESSAGE_BRIDGE_MODE=live CALENDAR_BRIDGE_MODE=live python3 app.py" \
    "$KENNY_ROOT/bridge"

# Wait a moment for bridge to initialize
sleep 2

# Start all agents in parallel
start_service "mail-agent" \
    "python3 -m uvicorn src.main:app --host 0.0.0.0 --port $MAIL_AGENT_PORT" \
    "$KENNY_ROOT/services/mail-agent"

start_service "contacts-agent" \
    "python3 -m uvicorn src.main:app --host 0.0.0.0 --port $CONTACTS_AGENT_PORT" \
    "$KENNY_ROOT/services/contacts-agent"

start_service "memory-agent" \
    "python3 -m uvicorn src.main:app --host 0.0.0.0 --port $MEMORY_AGENT_PORT" \
    "$KENNY_ROOT/services/memory-agent"

start_service "whatsapp-agent" \
    "python3 -m uvicorn src.main:app --host 0.0.0.0 --port $WHATSAPP_AGENT_PORT" \
    "$KENNY_ROOT/services/whatsapp-agent"

start_service "imessage-agent" \
    "python3 -m uvicorn src.main:app --host 0.0.0.0 --port $IMESSAGE_AGENT_PORT" \
    "$KENNY_ROOT/services/imessage-agent"

start_service "calendar-agent" \
    "PYTHONPATH=../../agent-sdk python3 main.py --port $CALENDAR_AGENT_PORT" \
    "$KENNY_ROOT/services/calendar-agent/src"

info "Agents starting up... (this takes a moment)"

# Phase 7: Start Dashboard
printf "\n${BLUE}=== Phase 7: Starting Dashboard ===${NC}\n"

start_service "dashboard" \
    "npm run dev" \
    "$KENNY_ROOT/services/dashboard"

# Wait for dashboard to be ready
wait_for_service "http://localhost:$DASHBOARD_PORT" "Dashboard" 20 || warn "Dashboard may need more time to start"

# Phase 8: Final Health Check
printf "\n${BLUE}=== Phase 8: System Health Check ===${NC}\n"

sleep 3  # Give services a moment to fully initialize

info "Running comprehensive health check..."
if [ -f "$KENNY_ROOT/kenny-health.sh" ]; then
    ./kenny-health.sh
else
    # Basic health check
    echo "Checking core services..."
    curl -s http://localhost:$GATEWAY_PORT/health > /dev/null && log "✓ Gateway healthy" || warn "✗ Gateway not responding"
    curl -s http://localhost:$AGENT_REGISTRY_PORT/health > /dev/null && log "✓ Registry healthy" || warn "✗ Registry not responding"  
    curl -s http://localhost:$COORDINATOR_PORT/health > /dev/null && log "✓ Coordinator healthy" || warn "✗ Coordinator not responding"
    curl -s http://localhost:$DASHBOARD_PORT > /dev/null && log "✓ Dashboard accessible" || warn "✗ Dashboard not accessible"
fi

# Success!
printf "\n${GREEN}🎉 Kenny v2.0 is now running!${NC}\n"
echo
printf "${BLUE}Access Kenny:${NC}\n"
echo "• Dashboard: http://localhost:$DASHBOARD_PORT"
echo "• Chat Interface: http://localhost:$DASHBOARD_PORT/query"
echo "• API Gateway: http://localhost:$GATEWAY_PORT"
echo "• System Health: http://localhost:$AGENT_REGISTRY_PORT/security/ui"
echo
printf "${BLUE}Quick Commands:${NC}\n"
echo "• Health Check: ./kenny-health.sh"
echo "• Service Status: ./kenny-status.sh"  
echo "• Stop Kenny: ./kenny-stop.sh"
echo
printf "${YELLOW}Logs are available in: $LOG_DIR${NC}\n"
printf "${YELLOW}PIDs are tracked in: $PID_DIR${NC}\n"
echo

info "Try asking Kenny: 'Show me my recent emails' or 'What meetings do I have today?'"
info "Kenny is ready to help! 🤖"

# Keep the script running to maintain services
printf "${BLUE}Kenny is running in the foreground. Press Ctrl+C to stop all services.${NC}\n"
wait