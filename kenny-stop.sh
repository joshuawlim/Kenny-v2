#!/bin/bash

# Kenny v2.0 - Clean Shutdown Script
# Gracefully stop all Kenny services
# Usage: ./kenny-stop.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KENNY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$KENNY_ROOT/pids"

# Service names (order matters for graceful shutdown)
SERVICES=(
    "dashboard"
    "bridge"
    "calendar-agent"
    "imessage-agent"
    "whatsapp-agent"
    "memory-agent"
    "contacts-agent"
    "mail-agent"
    "gateway"
    "coordinator"
    "agent-registry"
)

# Utility functions
log() {
    printf "${GREEN}✓ $1${NC}\n"
}

warn() {
    printf "${YELLOW}⚠ $1${NC}\n"
}

error() {
    printf "${RED}✗ $1${NC}\n"
}

info() {
    printf "${BLUE}ℹ $1${NC}\n"
}

# Stop a service gracefully
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        
        # Check if process is still running
        if ps -p $pid > /dev/null 2>&1; then
            info "Stopping $service_name (PID: $pid)..."
            
            # Try graceful shutdown first (SIGTERM)
            kill -TERM $pid 2>/dev/null
            
            # Wait up to 10 seconds for graceful shutdown
            local count=0
            while [ $count -lt 10 ] && ps -p $pid > /dev/null 2>&1; do
                sleep 1
                count=$((count + 1))
            done
            
            # If still running, force kill (SIGKILL)
            if ps -p $pid > /dev/null 2>&1; then
                warn "Force stopping $service_name..."
                kill -KILL $pid 2>/dev/null
                sleep 1
            fi
            
            # Verify it's stopped
            if ps -p $pid > /dev/null 2>&1; then
                error "Failed to stop $service_name"
                return 1
            else
                log "$service_name stopped successfully"
            fi
        else
            warn "$service_name was not running (stale PID file)"
        fi
        
        # Remove PID file
        rm -f "$pid_file"
    else
        info "$service_name was not running (no PID file)"
    fi
    
    return 0
}

# Stop all Kenny services by port (backup method)
stop_by_ports() {
    local ports=(8001 8002 9000 3001 5100 8000 8003 8004 8005 8006 8007)
    
    info "Checking for any remaining Kenny processes on known ports..."
    
    for port in "${ports[@]}"; do
        local pids=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            warn "Found process on port $port, stopping..."
            for pid in $pids; do
                kill -TERM $pid 2>/dev/null || true
                sleep 1
                if ps -p $pid > /dev/null 2>&1; then
                    kill -KILL $pid 2>/dev/null || true
                fi
            done
            log "Stopped processes on port $port"
        fi
    done
}

# Clean up temporary files and directories
cleanup_files() {
    info "Cleaning up temporary files..."
    
    # Remove log files older than 7 days
    if [ -d "$KENNY_ROOT/logs" ]; then
        find "$KENNY_ROOT/logs" -name "*.log" -mtime +7 -delete 2>/dev/null || true
        log "Cleaned old log files"
    fi
    
    # Clean up any temporary Python cache files
    find "$KENNY_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$KENNY_ROOT" -name "*.pyc" -delete 2>/dev/null || true
    
    # Clean up node_modules/.cache if it exists
    if [ -d "$KENNY_ROOT/services/dashboard/node_modules/.cache" ]; then
        rm -rf "$KENNY_ROOT/services/dashboard/node_modules/.cache" 2>/dev/null || true
    fi
    
    log "Temporary files cleaned up"
}

# Check if Kenny was launched with Docker
stop_docker_services() {
    if command -v docker &> /dev/null; then
        info "Checking for Docker Kenny services..."
        
        # Check if docker-compose is running Kenny services
        if [ -f "$KENNY_ROOT/infra/docker-compose.yml" ]; then
            cd "$KENNY_ROOT/infra"
            if docker-compose ps -q > /dev/null 2>&1; then
                local running_containers=$(docker-compose ps -q)
                if [ -n "$running_containers" ]; then
                    info "Stopping Docker Kenny services..."
                    docker-compose down
                    log "Docker services stopped"
                fi
            fi
            cd "$KENNY_ROOT"
        fi
        
        # Stop any Kenny-related containers
        local kenny_containers=$(docker ps --filter "label=service=kenny" -q 2>/dev/null || true)
        if [ -n "$kenny_containers" ]; then
            info "Stopping Kenny Docker containers..."
            docker stop $kenny_containers
            log "Kenny Docker containers stopped"
        fi
    fi
}

# Main function
main() {
    printf "${BLUE}"
    cat << "EOF"
 _  __                         ____  _               
| |/ /__ _ __  _ __  _   _     / ___|| |_ ___  _ __   
| ' // _ \ '_ \| '_ \| | | |   \___ \| __/ _ \| '_ \  
| . \  __/ | | | | | | |_| |    ___) | || (_) | |_) | 
|_|\_\___|_| |_|_| |_|\__, |   |____/ \__\___/| .__/  
                     |___/                   |_|     
EOF
    printf "${NC}\n"
    
    info "Kenny v2.0 Shutdown Process Starting..."
    
    # Create PID directory if it doesn't exist
    mkdir -p "$PID_DIR"
    
    # Check if any services are running
    local running_services=0
    for service in "${SERVICES[@]}"; do
        local pid_file="$PID_DIR/${service}.pid"
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if ps -p $pid > /dev/null 2>&1; then
                running_services=$((running_services + 1))
            fi
        fi
    done
    
    if [ $running_services -eq 0 ]; then
        # Check by ports as backup
        local port_processes=$(lsof -ti :8001,:8002,:9000,:3001,:5100,:8000,:8003,:8004,:8005,:8006,:8007 2>/dev/null | wc -l | tr -d ' ')
        if [ "$port_processes" -eq "0" ]; then
            info "Kenny is not currently running"
            exit 0
        else
            warn "Found Kenny processes running without PID files"
            stop_by_ports
            exit 0
        fi
    fi
    
    info "Found $running_services Kenny services running"
    
    # Stop Docker services if present
    stop_docker_services
    
    # Stop services in reverse order (graceful dependency shutdown)
    printf "\n${BLUE}=== Stopping Services ===${NC}\n"
    
    local stopped_count=0
    local failed_count=0
    
    for service in "${SERVICES[@]}"; do
        if stop_service "$service"; then
            stopped_count=$((stopped_count + 1))
        else
            failed_count=$((failed_count + 1))
        fi
    done
    
    # Backup: Stop any remaining processes by port
    stop_by_ports
    
    # Clean up files
    printf "\n${BLUE}=== Cleanup ===${NC}\n"
    cleanup_files
    
    # Final verification
    printf "\n${BLUE}=== Verification ===${NC}\n"
    local remaining_processes=$(lsof -ti :8001,:8002,:9000,:3001,:5100,:8000,:8003,:8004,:8005,:8006,:8007 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$remaining_processes" -eq "0" ]; then
        log "All Kenny services have been stopped successfully"
        echo
        printf "${GREEN}🛑 Kenny v2.0 has been shut down cleanly${NC}\n"
        
        if [ $failed_count -gt 0 ]; then
            warn "Note: $failed_count services required force termination"
        fi
        
    else
        warn "Some processes may still be running on Kenny ports"
        info "If you continue to have issues, you may need to restart your terminal"
        info "or check for any lingering processes manually"
    fi
    
    echo
    printf "${BLUE}Summary:${NC}\n"
    echo "• Services stopped: $stopped_count"
    if [ $failed_count -gt 0 ]; then
        echo "• Services force-stopped: $failed_count"
    fi
    echo "• Remaining processes: $remaining_processes"
    echo
    
    printf "${BLUE}To restart Kenny:${NC}\n"
    echo "• Run: ./kenny-launch.sh"
    echo
    
    info "Shutdown complete! 👋"
}

# Handle command line arguments
case "${1:-}" in
    --force)
        info "Force shutdown requested"
        stop_by_ports
        cleanup_files
        info "Force shutdown complete"
        exit 0
        ;;
    --docker)
        info "Docker-only shutdown requested"
        stop_docker_services
        info "Docker shutdown complete"
        exit 0
        ;;
    --help|-h)
        echo "Kenny v2.0 Stop Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  (no args)    Normal graceful shutdown"
        echo "  --force      Force stop all processes on Kenny ports"
        echo "  --docker     Stop only Docker services"
        echo "  --help       Show this help message"
        echo
        exit 0
        ;;
esac

# Run main function
main "$@"