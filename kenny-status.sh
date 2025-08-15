#!/bin/bash

# Kenny v2.0 - Service Status Monitor
# Real-time service status and monitoring
# Usage: ./kenny-status.sh [--watch]

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

# Parse service configuration
get_service_field() {
    local service_config="$1"
    local field_num="$2"
    echo "$service_config" | cut -d: -f$field_num
}

# Clear screen function
clear_screen() {
    if [ "$1" != "--no-clear" ]; then
        clear
    fi
}

# Check if service process is running
check_process() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo $pid
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Check service HTTP health
check_http_health() {
    local url="$1"
    
    local response=$(curl -s -w "%{http_code}" --max-time 3 "$url" 2>/dev/null)
    local http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Get service memory usage in MB
get_memory_usage() {
    local pid=$1
    if [ -n "$pid" ] && ps -p $pid > /dev/null 2>&1; then
        local memory_kb=$(ps -o rss= -p $pid 2>/dev/null | tr -d ' ')
        if [ -n "$memory_kb" ]; then
            echo "$((memory_kb / 1024))"
        else
            echo "0"
        fi
    else
        echo "0"
    fi
}

# Get service CPU usage percentage
get_cpu_usage() {
    local pid=$1
    if [ -n "$pid" ] && ps -p $pid > /dev/null 2>&1; then
        local cpu_usage=$(ps -o %cpu= -p $pid 2>/dev/null | tr -d ' ')
        if [ -n "$cpu_usage" ]; then
            printf "%.1f" "$cpu_usage"
        else
            echo "0.0"
        fi
    else
        echo "0.0"
    fi
}

# Get service uptime
get_uptime() {
    local pid=$1
    if [ -n "$pid" ] && ps -p $pid > /dev/null 2>&1; then
        local start_time=$(ps -o lstart= -p $pid 2>/dev/null | head -n1)
        if [ -n "$start_time" ]; then
            local start_epoch=$(date -j -f "%a %b %d %H:%M:%S %Y" "$start_time" +%s 2>/dev/null || echo "0")
            local current_epoch=$(date +%s)
            local uptime_seconds=$((current_epoch - start_epoch))
            
            if [ $uptime_seconds -gt 86400 ]; then
                echo "$((uptime_seconds / 86400))d $((uptime_seconds % 86400 / 3600))h"
            elif [ $uptime_seconds -gt 3600 ]; then
                echo "$((uptime_seconds / 3600))h $((uptime_seconds % 3600 / 60))m"
            elif [ $uptime_seconds -gt 60 ]; then
                echo "$((uptime_seconds / 60))m $((uptime_seconds % 60))s"
            else
                echo "${uptime_seconds}s"
            fi
        else
            echo "Unknown"
        fi
    else
        echo "Stopped"
    fi
}

# Check if port is listening
check_port_listening() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Sort services by priority
sort_services_by_priority() {
    local sorted=()
    
    # Priority 1 (Critical)
    for service_config in "${SERVICES[@]}"; do
        local priority=$(get_service_field "$service_config" 5)
        if [ "$priority" = "1" ]; then
            sorted+=("$service_config")
        fi
    done
    
    # Priority 2 (Important)
    for service_config in "${SERVICES[@]}"; do
        local priority=$(get_service_field "$service_config" 5)
        if [ "$priority" = "2" ]; then
            sorted+=("$service_config")
        fi
    done
    
    # Priority 3 (Optional)
    for service_config in "${SERVICES[@]}"; do
        local priority=$(get_service_field "$service_config" 5)
        if [ "$priority" = "3" ]; then
            sorted+=("$service_config")
        fi
    done
    
    printf '%s\n' "${sorted[@]}"
}

# Display service status table
display_status_table() {
    local show_header=${1:-true}
    
    if [ "$show_header" = "true" ]; then
        echo -e "${BLUE}=== Kenny v2.0 Service Status ===${NC}"
        echo -e "${CYAN}Updated: $(date)${NC}"
        echo
    fi
    
    # Table header
    printf "%-20s %-12s %-8s %-8s %-8s %-10s %-8s %-10s\n" \
        "Service" "Status" "Process" "HTTP" "Port" "Memory" "CPU%" "Uptime"
    printf "%-20s %-12s %-8s %-8s %-8s %-10s %-8s %-10s\n" \
        "-------" "------" "-------" "----" "----" "------" "----" "------"
    
    local total_services=0
    local running_services=0
    local healthy_services=0
    local critical_down=0
    
    # Process sorted services
    while IFS= read -r service_config; do
        total_services=$((total_services + 1))
        
        local service_name=$(get_service_field "$service_config" 1)
        local port=$(get_service_field "$service_config" 2)
        local endpoint=$(get_service_field "$service_config" 3)
        local display_name=$(get_service_field "$service_config" 4)
        local priority=$(get_service_field "$service_config" 5)
        local url="http://localhost:${port}${endpoint}"
        
        # Check process status
        local pid=$(check_process "$service_name")
        local process_status="STOPPED"
        local process_color=$RED
        
        if [ -n "$pid" ]; then
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
        
        # Check port status
        local port_status="CLOSED"
        local port_color=$RED
        if check_port_listening "$port"; then
            port_status="OPEN"
            port_color=$GREEN
        elif [ "$process_status" = "STOPPED" ]; then
            port_status="N/A"
            port_color=$YELLOW
        fi
        
        # Calculate overall status
        local overall_status="DOWN"
        local overall_color=$RED
        if [ "$process_status" = "RUNNING" ] && [ "$http_status" = "OK" ]; then
            overall_status="HEALTHY"
            overall_color=$GREEN
        elif [ "$process_status" = "RUNNING" ]; then
            overall_status="DEGRADED"
            overall_color=$YELLOW
        else
            # Check if this is a critical service
            if [ "$priority" = "1" ]; then
                critical_down=$((critical_down + 1))
            fi
        fi
        
        # Get resource usage
        local memory=$(get_memory_usage "$pid")
        local cpu=$(get_cpu_usage "$pid")
        local uptime=$(get_uptime "$pid")
        
        # Format memory with unit
        local memory_display="N/A"
        if [ "$memory" != "0" ]; then
            if [ "$memory" -gt 1024 ]; then
                memory_display="$(echo "$memory" | awk '{printf "%.1fGB", $1/1024}')"
            else
                memory_display="${memory}MB"
            fi
        fi
        
        # Print service status row
        printf "%-20s " "$display_name"
        printf "${overall_color}%-12s${NC} " "$overall_status"
        printf "${process_color}%-8s${NC} " "$process_status"
        printf "${http_color}%-8s${NC} " "$http_status"
        printf "${port_color}%-8s${NC} " "$port_status"
        printf "%-10s " "$memory_display"
        printf "%-8s " "${cpu}%"
        printf "%-10s\n" "$uptime"
        
    done < <(sort_services_by_priority)
    
    echo
    
    # Status summary
    echo -e "${BLUE}=== System Summary ===${NC}"
    echo -e "Services Running: ${GREEN}$running_services${NC}/$total_services"
    echo -e "Services Healthy: ${GREEN}$healthy_services${NC}/$total_services"
    
    if [ $critical_down -gt 0 ]; then
        echo -e "Critical Services Down: ${RED}$critical_down${NC}"
        echo -e "System Status: ${RED}CRITICAL${NC}"
    elif [ $running_services -eq $total_services ] && [ $healthy_services -eq $total_services ]; then
        echo -e "System Status: ${GREEN}OPERATIONAL${NC} 🎉"
    elif [ $running_services -gt 0 ]; then
        echo -e "System Status: ${YELLOW}DEGRADED${NC}"
    else
        echo -e "System Status: ${RED}DOWN${NC}"
    fi
    
    echo
}

# Display quick URLs
display_quick_access() {
    echo -e "${BLUE}=== Quick Access URLs ===${NC}"
    echo "• Dashboard:      http://localhost:3001"
    echo "• Chat Interface: http://localhost:3001/query"
    echo "• API Gateway:    http://localhost:9000"
    echo "• Health API:     http://localhost:9000/health"
    echo "• Agent Registry: http://localhost:8001"
    echo "• Security UI:    http://localhost:8001/security/ui"
    echo
}

# Display system resources
display_system_resources() {
    echo -e "${BLUE}=== System Resources ===${NC}"
    
    # Total Kenny memory usage
    local total_memory=0
    for service_config in "${SERVICES[@]}"; do
        local service_name=$(get_service_field "$service_config" 1)
        local pid=$(check_process "$service_name")
        if [ -n "$pid" ]; then
            local memory=$(get_memory_usage "$pid")
            total_memory=$((total_memory + memory))
        fi
    done
    
    local total_memory_display="$total_memory MB"
    if [ $total_memory -gt 1024 ]; then
        total_memory_display="$(echo "$total_memory" | awk '{printf "%.1f GB", $1/1024}')"
    fi
    
    # System load
    local system_load=$(uptime | sed 's/.*load averages: //')
    
    echo "• Kenny Memory Usage: $total_memory_display"
    echo "• System Load: $system_load"
    echo "• Active Connections: $(netstat -an | grep LISTEN | wc -l | tr -d ' ') ports listening"
    echo
}

# Watch mode - continuous monitoring
watch_mode() {
    info "Starting continuous monitoring... (Press Ctrl+C to exit)"
    echo
    
    while true; do
        clear_screen
        
        echo -e "${BLUE}"
        cat << "EOF"
 _  __                         ____  _        _             
| |/ /__ _ __  _ __  _   _     / ___|| |_ __ _| |_ _   _ ___ 
| ' // _` | '_ \| '_ \| | | |   \___ \| __/ _` | __| | | / __|
| . \ (_| | | | | | | | |_| |    ___) | || (_| | |_| |_| \__ \
|_|\_\__,_|_| |_|_| |_|\__, |   |____/ \__\__,_|\__|\__,_|___/
                       |___/                                 
EOF
        echo -e "${NC}"
        
        display_status_table true
        display_system_resources
        display_quick_access
        
        echo -e "${CYAN}Refreshing in 5 seconds... (Ctrl+C to exit)${NC}"
        sleep 5
    done
}

# JSON output for programmatic use
json_output() {
    echo "{"
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"services\": ["
    
    local first=true
    for service_config in "${SERVICES[@]}"; do
        if [ "$first" = false ]; then
            echo ","
        fi
        first=false
        
        local service_name=$(get_service_field "$service_config" 1)
        local port=$(get_service_field "$service_config" 2)
        local endpoint=$(get_service_field "$service_config" 3)
        local display_name=$(get_service_field "$service_config" 4)
        local priority=$(get_service_field "$service_config" 5)
        local url="http://localhost:${port}${endpoint}"
        
        local pid=$(check_process "$service_name")
        local running=$([ -n "$pid" ] && echo "true" || echo "false")
        local healthy=$(check_http_health "$url" && echo "true" || echo "false")
        local memory=$(get_memory_usage "$pid")
        
        echo "    {"
        echo "      \"name\": \"$service_name\","
        echo "      \"display_name\": \"$display_name\","
        echo "      \"running\": $running,"
        echo "      \"healthy\": $healthy,"
        echo "      \"pid\": $([ -n "$pid" ] && echo "$pid" || echo "null"),"
        echo "      \"memory_mb\": $memory,"
        echo "      \"priority\": $priority,"
        echo "      \"port\": $port"
        echo -n "    }"
    done
    echo ""
    echo "  ]"
    echo "}"
}

# Main function
main() {
    # Handle command line arguments
    case "${1:-}" in
        --watch|-w)
            watch_mode
            exit 0
            ;;
        --json)
            json_output
            exit 0
            ;;
        --help|-h)
            echo "Kenny v2.0 Service Status Monitor"
            echo
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  (no args)    Show current status"
            echo "  --watch, -w  Continuous monitoring mode"
            echo "  --json       JSON output for scripts"
            echo "  --help, -h   Show this help message"
            echo
            echo "Examples:"
            echo "  $0                 # One-time status check"
            echo "  $0 --watch         # Continuous monitoring"
            echo "  $0 --json | jq .   # JSON output with formatting"
            echo
            exit 0
            ;;
    esac
    
    # Single status check
    clear_screen --no-clear
    
    echo -e "${BLUE}"
    cat << "EOF"
 _  __                         ____  _        _             
| |/ /__ _ __  _ __  _   _     / ___|| |_ __ _| |_ _   _ ___ 
| ' // _` | '_ \| '_ \| | | |   \___ \| __/ _` | __| | | / __|
| . \ (_| | | | | | | | |_| |    ___) | || (_| | |_| |_| \__ \
|_|\_\__,_|_| |_|_| |_|\__, |   |____/ \__\__,_|\__|\__,_|___/
                       |___/                                 
EOF
    echo -e "${NC}"
    
    info "Kenny v2.0 Service Status Check"
    echo
    
    display_status_table true
    display_system_resources
    display_quick_access
    
    echo -e "${BLUE}Commands:${NC}"
    echo "• Full Health Check: ./kenny-health.sh"
    echo "• Start Kenny:       ./kenny-launch.sh"
    echo "• Stop Kenny:        ./kenny-stop.sh"
    echo "• Continuous Watch:  ./kenny-status.sh --watch"
    echo
}

# Handle Ctrl+C gracefully in watch mode
trap 'echo -e "\n${BLUE}Monitoring stopped. Kenny services continue running.${NC}"; exit 0' SIGINT

# Run main function
main "$@"