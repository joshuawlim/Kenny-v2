#!/bin/bash

# Kenny v2.0 - System Health Check
# Comprehensive health monitoring for all Kenny services
# Usage: ./kenny-health.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KENNY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$KENNY_ROOT/pids"

# Service configurations (service:port:endpoint:display_name:priority)
SERVICES=(
    "agent-registry:8001:/health:Agent Registry:1"
    "coordinator:8002:/health:Coordinator:1"
    "gateway:9000:/health:API Gateway:1"
    "dashboard:3001:/:React Dashboard:2"
    "bridge:5100:/:Data Bridge:2"
    "mail-agent:8000:/health:Mail Agent:2"
    "contacts-agent:8003:/health:Contacts Agent:2"
    "memory-agent:8004:/health:Memory Agent:2"
    "whatsapp-agent:8005:/health:WhatsApp Agent:3"
    "imessage-agent:8006:/health:iMessage Agent:3"
    "calendar-agent:8007:/health:Calendar Agent:3"
)

# Parse service configuration
get_service_field() {
    local service_config="$1"
    local field_num="$2"
    echo "$service_config" | cut -d: -f$field_num
}

# Utility functions
log() {
    echo -e "${GREEN}✓ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if service process is running
check_process() {
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

# Check service HTTP health endpoint
check_http_health() {
    local url="$1"
    
    # Try HTTP request with timeout
    local response=$(curl -s -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
    local http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Get service memory usage
get_memory_usage() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            # Get memory usage in MB on macOS
            local memory_kb=$(ps -o rss= -p $pid 2>/dev/null | tr -d ' ')
            if [ -n "$memory_kb" ]; then
                echo "$((memory_kb / 1024))MB"
            else
                echo "N/A"
            fi
        else
            echo "N/A"
        fi
    else
        echo "N/A"
    fi
}

# Get service uptime
get_uptime() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            # Get process start time and calculate uptime
            local start_time=$(ps -o lstart= -p $pid 2>/dev/null | head -n1)
            if [ -n "$start_time" ]; then
                local start_epoch=$(date -j -f "%a %b %d %H:%M:%S %Y" "$start_time" +%s 2>/dev/null || echo "0")
                local current_epoch=$(date +%s)
                local uptime_seconds=$((current_epoch - start_epoch))
                
                if [ $uptime_seconds -gt 3600 ]; then
                    echo "$((uptime_seconds / 3600))h $((uptime_seconds % 3600 / 60))m"
                elif [ $uptime_seconds -gt 60 ]; then
                    echo "$((uptime_seconds / 60))m $((uptime_seconds % 60))s"
                else
                    echo "${uptime_seconds}s"
                fi
            else
                echo "N/A"
            fi
        else
            echo "Stopped"
        fi
    else
        echo "Stopped"
    fi
}

# Test basic Kenny functionality
test_kenny_functionality() {
    info "Testing Kenny functionality..."
    
    # Test Gateway health aggregation
    local gateway_health=$(curl -s http://localhost:9000/health 2>/dev/null)
    if [ $? -eq 0 ]; then
        log "Gateway health endpoint responding"
    else
        error "Gateway health endpoint not responding"
        return 1
    fi
    
    # Test agent discovery via Gateway
    local agents_response=$(curl -s http://localhost:9000/agents 2>/dev/null)
    if [ $? -eq 0 ] && echo "$agents_response" | grep -q "agents"; then
        local agent_count=$(echo "$agents_response" | grep -o '"agent_id"' | wc -l | tr -d ' ')
        log "Gateway can discover $agent_count agents"
    else
        warn "Gateway agent discovery may have issues"
    fi
    
    # Test Dashboard accessibility
    local dashboard_response=$(curl -s -w "%{http_code}" http://localhost:3001 2>/dev/null)
    local dashboard_code="${dashboard_response: -3}"
    if [ "$dashboard_code" = "200" ]; then
        log "Dashboard is accessible"
    else
        warn "Dashboard may not be fully loaded yet"
    fi
    
    # Test Registry security dashboard
    local security_response=$(curl -s -w "%{http_code}" http://localhost:8001/security/ui 2>/dev/null)
    local security_code="${security_response: -3}"
    if [ "$security_code" = "200" ]; then
        log "Security dashboard is accessible"
    else
        warn "Security dashboard may have issues"
    fi
    
    return 0
}

# Check external dependencies
check_dependencies() {
    info "Checking external dependencies..."
    
    # Check Ollama
    if command -v ollama &> /dev/null; then
        if pgrep -f "ollama serve" > /dev/null; then
            log "Ollama service is running"
        else
            warn "Ollama is installed but service is not running"
            info "Start with: ollama serve"
        fi
    else
        warn "Ollama not installed (install with: brew install ollama)"
    fi
    
    # Check Python version
    local python_version=$(python3 --version 2>/dev/null | cut -d' ' -f2)
    if [ -n "$python_version" ]; then
        log "Python: $python_version"
    else
        error "Python 3 not found"
    fi
    
    # Check Node.js version
    local node_version=$(node --version 2>/dev/null)
    if [ -n "$node_version" ]; then
        log "Node.js: $node_version"
    else
        error "Node.js not found"
    fi
    
    # Check macOS permissions (basic check)
    if [ "$(uname)" = "Darwin" ]; then
        info "macOS detected - ensure Kenny has necessary permissions:"
        info "  • Full Disk Access for Terminal/iTerm"
        info "  • Accessibility permissions for automation"
        info "  • Automation permissions for Mail/Calendar apps"
    fi
}

# Main health check
main() {
    echo -e "${BLUE}"
    cat << "EOF"
 _  __                         _   _            _ _   _     
| |/ /__ _ __  _ __  _   _     | | | | ___  __ _| | |_| |__  
| ' // _` | '_ \| '_ \| | | |   | |_| |/ _ \/ _` | | __| '_ \ 
| . \ (_| | | | | | | | |_| |   |  _  |  __/ (_| | | |_| | | |
|_|\_\__,_|_| |_|_| |_|\__, |   |_| |_|\___|\__,_|_|\__|_| |_|
                       |___/                                 
EOF
    echo -e "${NC}"
    
    info "Kenny v2.0 System Health Check"
    info "Timestamp: $(date)"
    echo
    
    # Service Status Table
    echo -e "${BLUE}=== Service Status ===${NC}"
    printf "%-20s %-10s %-10s %-10s %-10s\n" "Service" "Process" "HTTP" "Memory" "Uptime"
    printf "%-20s %-10s %-10s %-10s %-10s\n" "-------" "-------" "----" "------" "------"
    
    local total_services=0
    local running_services=0
    local healthy_services=0
    
    for service_config in "${SERVICES[@]}"; do
        total_services=$((total_services + 1))
        
        local service_name=$(get_service_field "$service_config" 1)
        local port=$(get_service_field "$service_config" 2)
        local endpoint=$(get_service_field "$service_config" 3)
        local display_name=$(get_service_field "$service_config" 4)
        local url="http://localhost:${port}${endpoint}"
        
        # Check process status
        local process_status="STOPPED"
        local process_color=$RED
        if check_process "$service_name"; then
            process_status="RUNNING"
            process_color=$GREEN
            running_services=$((running_services + 1))
        fi
        
        # Check HTTP health
        local http_status="FAIL"
        local http_color=$RED
        if check_http_health "$url"; then
            http_status="OK"
            http_color=$GREEN
            healthy_services=$((healthy_services + 1))
        elif [ "$process_status" = "STOPPED" ]; then
            http_status="N/A"
            http_color=$YELLOW
        fi
        
        # Get resource usage
        local memory=$(get_memory_usage "$service_name")
        local uptime=$(get_uptime "$service_name")
        
        # Print service status
        printf "%-20s " "$display_name"
        printf "${process_color}%-10s${NC} " "$process_status"
        printf "${http_color}%-10s${NC} " "$http_status"
        printf "%-10s " "$memory"
        printf "%-10s\n" "$uptime"
    done
    
    echo
    
    # Summary
    echo -e "${BLUE}=== System Summary ===${NC}"
    log "Services Running: $running_services/$total_services"
    log "Services Healthy: $healthy_services/$total_services"
    
    if [ $running_services -eq $total_services ] && [ $healthy_services -eq $total_services ]; then
        log "Kenny v2.0 is fully operational! 🎉"
    elif [ $running_services -gt 0 ]; then
        warn "Kenny is partially operational (some services may be starting up)"
    else
        error "Kenny is not running - use './kenny-launch.sh' to start"
        exit 1
    fi
    
    echo
    
    # External Dependencies
    echo -e "${BLUE}=== Dependencies Check ===${NC}"
    check_dependencies
    echo
    
    # Functionality Tests (only if services are running)
    if [ $running_services -gt 0 ]; then
        echo -e "${BLUE}=== Functionality Tests ===${NC}"
        test_kenny_functionality
        echo
    fi
    
    # Quick Access URLs
    echo -e "${BLUE}=== Quick Access ===${NC}"
    echo "• Main Dashboard: http://localhost:3001"
    echo "• Chat Interface: http://localhost:3001/query"
    echo "• API Gateway: http://localhost:9000"
    echo "• Agent Registry: http://localhost:8001"
    echo "• Security Dashboard: http://localhost:8001/security/ui"
    echo "• System Health API: http://localhost:8001/system/health/dashboard"
    echo
    
    # Troubleshooting hints
    if [ $healthy_services -lt $total_services ]; then
        echo -e "${YELLOW}=== Troubleshooting Hints ===${NC}"
        warn "If services are not healthy:"
        echo "  1. Check logs in: $KENNY_ROOT/logs/"
        echo "  2. Verify ports are not in use by other applications"
        echo "  3. Ensure all dependencies are installed"
        echo "  4. Try restarting: ./kenny-stop.sh && ./kenny-launch.sh"
        echo "  5. Check macOS permissions for Terminal/iTerm"
    fi
    
    echo -e "${GREEN}Health check completed!${NC}"
}

# Run main function
main "$@"