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

# Phase 3.5 Configuration Management
load_phase35_config() {
    # Load .env.phase35 if it exists
    if [ -f "$KENNY_ROOT/.env.phase35" ]; then
        info "Loading Phase 3.5 configuration from .env.phase35..."
        # Source the file but don't export variables automatically
        while IFS= read -r line; do
            # Skip comments and empty lines
            if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "$line" ]]; then
                continue
            fi
            # Export the variable
            if [[ "$line" =~ ^[A-Z_]+=.*$ ]]; then
                export "$line"
            fi
        done < "$KENNY_ROOT/.env.phase35"
        log "Phase 3.5 configuration loaded"
    else
        info "No .env.phase35 file found, using environment defaults"
    fi
    
    # Validate configuration if validation script exists
    if [ -f "$KENNY_ROOT/scripts/validate-phase35-config.sh" ]; then
        info "Validating Phase 3.5 configuration..."
        if "$KENNY_ROOT/scripts/validate-phase35-config.sh" > /dev/null 2>&1; then
            log "Phase 3.5 configuration validation passed"
        else
            warn "Phase 3.5 configuration validation failed - check settings"
            warn "Run './scripts/validate-phase35-config.sh' for details"
        fi
    fi
}

# Load configuration early (after utility functions are defined)

# Phase 3.5 Configuration
PHASE35_ENABLED=${KENNY_PHASE35_ENABLED:-true}
PHASE35_DATABASE_PATH=${KENNY_PHASE35_DATABASE_PATH:-"$KENNY_ROOT/services/calendar-agent/calendar.db"}
PHASE35_PERFORMANCE_MODE=${KENNY_PHASE35_PERFORMANCE_MODE:-auto}
PHASE35_EVENTKIT_PERMISSIONS=${KENNY_PHASE35_EVENTKIT_PERMISSIONS:-auto}

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

# Phase 3.5 specific functions
check_eventkit_permissions() {
    info "Checking EventKit permissions for Phase 3.5..."
    
    # Create a temporary Python script to check EventKit permissions
    local python_check=$(cat << 'EOF'
import sys
try:
    from EventKit import (EKEventStore, EKEntityTypeEvent, 
                         EKAuthorizationStatusNotDetermined, EKAuthorizationStatusDenied,
                         EKAuthorizationStatusRestricted, EKAuthorizationStatusAuthorized,
                         EKAuthorizationStatusWriteOnly)
    from Foundation import NSRunLoop, NSDate
    import objc
    
    # Create event store
    store = EKEventStore.alloc().init()
    
    # Check current authorization status - use the integer constant directly
    status = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
    
    if status == EKAuthorizationStatusNotDetermined:
        print("PERMISSION_NEEDED")
        # Request permission (this will show the system dialog)
        def completion_handler(granted, error):
            if granted:
                print("PERMISSION_GRANTED")
            else:
                print("PERMISSION_DENIED")
            NSRunLoop.currentRunLoop().stop()
        
        store.requestAccessToEntityType_completion_(EKEntityTypeEvent, completion_handler)
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(10.0))
        
    elif status == EKAuthorizationStatusDenied:
        print("PERMISSION_DENIED")
        sys.exit(1)
    elif status == EKAuthorizationStatusRestricted:
        print("PERMISSION_RESTRICTED")
        sys.exit(1)
    elif status == EKAuthorizationStatusAuthorized or status == EKAuthorizationStatusWriteOnly:
        print("PERMISSION_GRANTED")
    else:
        print("PERMISSION_UNKNOWN")
        sys.exit(1)
        
except ImportError:
    print("EVENTKIT_NOT_AVAILABLE")
    sys.exit(2)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(3)
EOF
)
    
    local permission_result
    permission_result=$(python3 -c "$python_check" 2>/dev/null)
    local exit_code=$?
    
    case "$permission_result" in
        "PERMISSION_GRANTED")
            log "EventKit permissions granted"
            return 0
            ;;
        "PERMISSION_NEEDED")
            warn "EventKit permissions required - please grant access in the system dialog"
            return 1
            ;;
        "PERMISSION_DENIED")
            warn "EventKit permissions denied - Phase 3.5 will fallback to Phase 3.2 mode"
            return 2
            ;;
        "PERMISSION_RESTRICTED")
            warn "EventKit permissions restricted - Phase 3.5 disabled"
            return 2
            ;;
        "EVENTKIT_NOT_AVAILABLE")
            warn "EventKit framework not available - installing dependencies"
            pip3 install pyobjc-framework-EventKit >> "$LOG_DIR/eventkit-install.log" 2>&1
            return 3
            ;;
        *)
            error "Failed to check EventKit permissions: $permission_result"
            return 3
            ;;
    esac
}

initialize_phase35_database() {
    info "Initializing Phase 3.5 calendar database..."
    
    # Create calendar-agent directory if it doesn't exist
    mkdir -p "$(dirname "$PHASE35_DATABASE_PATH")"
    
    # Initialize database using calendar_database.py
    local init_script=$(cat << 'EOF'
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'calendar-agent', 'src'))

try:
    from calendar_database import CalendarDatabase, DatabaseConfig
    import asyncio
    
    async def init_db():
        config = DatabaseConfig(
            database_path=os.environ.get('PHASE35_DATABASE_PATH', 'calendar.db'),
            connection_pool_size=10,
            timeout=30.0,
            journal_mode="WAL",
            synchronous="NORMAL",
            cache_size=-64000,
            temp_store="MEMORY",
            enable_fts=True,
            backup_enabled=True
        )
        
        db = CalendarDatabase(config)
        await db.initialize()
        
        # Test basic functionality
        start_time = time.time()
        events = await db.get_events_in_range(
            datetime.now() - timedelta(days=7),
            datetime.now() + timedelta(days=7)
        )
        query_time = (time.time() - start_time) * 1000
        
        print(f"DATABASE_INITIALIZED")
        print(f"QUERY_TIME_MS:{query_time:.2f}")
        print(f"EVENTS_COUNT:{len(events)}")
        
        await db.close()
        
    asyncio.run(init_db())
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOF
)
    
    local db_result
    export PHASE35_DATABASE_PATH
    db_result=$(python3 -c "$init_script" 2>/dev/null)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log "Phase 3.5 database initialized successfully"
        local query_time=$(echo "$db_result" | grep "QUERY_TIME_MS:" | cut -d: -f2)
        local events_count=$(echo "$db_result" | grep "EVENTS_COUNT:" | cut -d: -f2)
        
        if [ -n "$query_time" ]; then
            info "Initial query performance: ${query_time}ms"
            if (( $(echo "$query_time < 10" | bc -l) )); then
                log "Performance target achieved (<10ms)"
            else
                warn "Performance target not met (${query_time}ms > 10ms)"
            fi
        fi
        
        return 0
    else
        error "Failed to initialize Phase 3.5 database: $db_result"
        return 1
    fi
}

test_phase35_components() {
    info "Testing Phase 3.5 component integration..."
    
    local test_script=$(cat << 'EOF'
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'calendar-agent', 'src'))

try:
    from week2_integration_coordinator import Week2IntegrationCoordinator
    from calendar_database import CalendarDatabase, DatabaseConfig
    import asyncio
    import time
    
    async def test_components():
        # Test database
        config = DatabaseConfig(database_path=os.environ.get('PHASE35_DATABASE_PATH', 'calendar.db'))
        db = CalendarDatabase(config)
        await db.initialize()
        
        # Test coordinator
        coordinator = Week2IntegrationCoordinator(database=db)
        await coordinator.start()
        
        # Run basic health check
        health = await coordinator.get_health_status()
        
        print(f"COMPONENTS_HEALTHY:{health.get('healthy', False)}")
        print(f"SYNC_ENGINE_STATUS:{health.get('sync_engine_status', 'unknown')}")
        print(f"DATABASE_STATUS:{health.get('database_status', 'unknown')}")
        print(f"PERFORMANCE_MODE:{health.get('performance_mode', 'unknown')}")
        
        await coordinator.stop()
        await db.close()
        
    asyncio.run(test_components())
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOF
)
    
    local test_result
    export PHASE35_DATABASE_PATH
    test_result=$(python3 -c "$test_script" 2>/dev/null)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        local healthy=$(echo "$test_result" | grep "COMPONENTS_HEALTHY:" | cut -d: -f2)
        if [ "$healthy" = "True" ]; then
            log "Phase 3.5 components are healthy"
            return 0
        else
            warn "Phase 3.5 components are not fully healthy"
            return 1
        fi
    else
        error "Phase 3.5 component test failed: $test_result"
        return 1
    fi
}

enable_phase35_mode() {
    info "Enabling Phase 3.5 high-performance mode..."
    export KENNY_PHASE35_ENABLED=true
    export KENNY_CALENDAR_PERFORMANCE_MODE=phase35
    export KENNY_DATABASE_PATH="$PHASE35_DATABASE_PATH"
    log "Phase 3.5 mode enabled"
}

fallback_to_phase32() {
    warn "Falling back to Phase 3.2 mode..."
    export KENNY_PHASE35_ENABLED=false
    export KENNY_CALENDAR_PERFORMANCE_MODE=phase32
    unset KENNY_DATABASE_PATH
    warn "Running in Phase 3.2 compatibility mode"
}

# Load Phase 3.5 configuration now that utility functions are defined
load_phase35_config

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

# Phase 4.5: Phase 3.5 Calendar Database + Real-time Sync Initialization
if [ "$PHASE35_ENABLED" = "true" ]; then
    printf "\n${BLUE}=== Phase 4.5: Phase 3.5 Calendar Database + Real-time Sync ===${NC}\n"
    
    # Check and handle EventKit permissions
    if [ "$PHASE35_EVENTKIT_PERMISSIONS" = "auto" ]; then
        if check_eventkit_permissions; then
            log "EventKit permissions verified"
        else
            permission_exit_code=$?
            case $permission_exit_code in
                1)
                    info "Waiting for user to grant EventKit permissions..."
                    sleep 3
                    if check_eventkit_permissions; then
                        log "EventKit permissions granted after user approval"
                    else
                        warn "EventKit permissions still not granted - falling back to Phase 3.2"
                        fallback_to_phase32
                    fi
                    ;;
                2)
                    warn "EventKit permissions denied/restricted - falling back to Phase 3.2"
                    fallback_to_phase32
                    ;;
                3)
                    warn "EventKit not available - attempting to install dependencies"
                    if check_eventkit_permissions; then
                        log "EventKit dependencies installed successfully"
                    else
                        warn "EventKit installation failed - falling back to Phase 3.2"
                        fallback_to_phase32
                    fi
                    ;;
            esac
        fi
    fi
    
    # Initialize Phase 3.5 database if still enabled
    if [ "$KENNY_PHASE35_ENABLED" != "false" ]; then
        if initialize_phase35_database; then
            log "Phase 3.5 database initialization completed"
            
            # Test component integration
            if test_phase35_components; then
                log "Phase 3.5 component integration verified"
                enable_phase35_mode
                info "Phase 3.5 high-performance mode is active!"
                info "Expected performance: <0.01s query times, real-time sync"
            else
                warn "Phase 3.5 component integration failed - falling back to Phase 3.2"
                fallback_to_phase32
            fi
        else
            warn "Phase 3.5 database initialization failed - falling back to Phase 3.2"
            fallback_to_phase32
        fi
    fi
else
    info "Phase 3.5 disabled by configuration - using Phase 3.2 mode"
    fallback_to_phase32
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

# Start all agents in parallel (using intelligent agents by default)
start_service "mail-agent" \
    "KENNY_INTELLIGENT_AGENTS=true KENNY_LLM_MODEL=llama3.2:3b python3 -m uvicorn src.main:app --host 0.0.0.0 --port $MAIL_AGENT_PORT" \
    "$KENNY_ROOT/services/mail-agent"

start_service "contacts-agent" \
    "KENNY_INTELLIGENT_AGENTS=true KENNY_LLM_MODEL=llama3.2:3b python3 -m uvicorn src.main:app --host 0.0.0.0 --port $CONTACTS_AGENT_PORT" \
    "$KENNY_ROOT/services/contacts-agent"

start_service "memory-agent" \
    "KENNY_LLM_MODEL=llama3.2:3b python3 -m uvicorn src.main:app --host 0.0.0.0 --port $MEMORY_AGENT_PORT" \
    "$KENNY_ROOT/services/memory-agent"

start_service "whatsapp-agent" \
    "KENNY_LLM_MODEL=llama3.2:3b python3 -m uvicorn src.main:app --host 0.0.0.0 --port $WHATSAPP_AGENT_PORT" \
    "$KENNY_ROOT/services/whatsapp-agent"

start_service "imessage-agent" \
    "KENNY_INTELLIGENT_AGENTS=true KENNY_LLM_MODEL=llama3.2:3b python3 -m uvicorn src.main:app --host 0.0.0.0 --port $IMESSAGE_AGENT_PORT" \
    "$KENNY_ROOT/services/imessage-agent"

start_service "calendar-agent" \
    "KENNY_INTELLIGENT_AGENTS=true KENNY_LLM_MODEL=llama3.2:3b PYTHONPATH=../../agent-sdk KENNY_PHASE35_ENABLED=$KENNY_PHASE35_ENABLED KENNY_CALENDAR_PERFORMANCE_MODE=$KENNY_CALENDAR_PERFORMANCE_MODE KENNY_DATABASE_PATH=$KENNY_DATABASE_PATH python3 main.py --port $CALENDAR_AGENT_PORT" \
    "$KENNY_ROOT/services/calendar-agent/src"

info "Agents starting up... (this takes a moment)"

# Phase 7: Start Dashboard
printf "\n${BLUE}=== Phase 7: Starting Dashboard ===${NC}\n"

# Check if dashboard build is needed
if [ -d "$KENNY_ROOT/services/dashboard" ]; then
    cd "$KENNY_ROOT/services/dashboard"
    
    # Check if TypeScript files exist and need compilation
    if [ ! -d "dist" ] && [ -f "tsconfig.json" ]; then
        info "Building dashboard for first run..."
        npm run build >> "$LOG_DIR/dashboard-build.log" 2>&1
        log "Dashboard build complete"
    fi
    
    cd "$KENNY_ROOT"
fi

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

# Display active performance mode
if [ "$KENNY_PHASE35_ENABLED" = "true" ]; then
    printf "\n${GREEN}⚡ Phase 3.5 High-Performance Mode Active!${NC}\n"
    echo "• Calendar Database: Real-time sync with <0.01s queries"
    echo "• EventKit Integration: Bidirectional sync enabled"
    echo "• Database Path: $KENNY_DATABASE_PATH"
    echo "• Expected Performance: Sub-10ms query times"
else
    printf "\n${YELLOW}📊 Phase 3.2 Compatibility Mode Active${NC}\n"
    echo "• Standard performance mode"
    echo "• Phase 3.5 features disabled or unavailable"
fi

echo
printf "${BLUE}Access Kenny:${NC}\n"
echo "• Dashboard: http://localhost:$DASHBOARD_PORT"
echo "• Chat Interface: http://localhost:$DASHBOARD_PORT/chat"
echo "• API Gateway: http://localhost:$GATEWAY_PORT"
echo "• System Health: http://localhost:$AGENT_REGISTRY_PORT/system/health/dashboard"
echo
printf "${BLUE}Quick Commands:${NC}\n"
echo "• Health Check: ./kenny-health.sh"
echo "• Service Status: ./kenny-status.sh"
if [ "$KENNY_PHASE35_ENABLED" = "true" ]; then
    echo "• Phase 3.5 Test: ./kenny-test-phase35.sh"
    echo "• Phase 3.5 Status: ./kenny-status.sh --phase35"
fi
echo "• Stop Kenny: ./kenny-stop.sh"
echo
printf "${YELLOW}Logs are available in: $LOG_DIR${NC}\n"
printf "${YELLOW}PIDs are tracked in: $PID_DIR${NC}\n"
echo

info "Try asking Kenny: 'Show me my recent emails' or 'What meetings do I have today?'"
if [ "$KENNY_PHASE35_ENABLED" = "true" ]; then
    info "With Phase 3.5, calendar queries should respond in under 10ms!"
fi
info "Kenny is ready to help! 🤖"

# Keep the script running to maintain services
printf "${BLUE}Kenny is running in the foreground. Press Ctrl+C to stop all services.${NC}\n"
wait