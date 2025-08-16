#!/bin/bash

# Kenny v2.0 - Phase 3.5 Configuration Validation
# Validates Phase 3.5 environment variables and configuration
# Usage: ./scripts/validate-phase35-config.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KENNY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Validation results
VALID_COUNT=0
INVALID_COUNT=0
WARNING_COUNT=0

# Utility functions
log_valid() {
    printf "${GREEN}[VALID] %s${NC}\n" "$1"
    VALID_COUNT=$((VALID_COUNT + 1))
}

log_invalid() {
    printf "${RED}[INVALID] %s${NC}\n" "$1"
    INVALID_COUNT=$((INVALID_COUNT + 1))
}

log_warning() {
    printf "${YELLOW}[WARNING] %s${NC}\n" "$1"
    WARNING_COUNT=$((WARNING_COUNT + 1))
}

log_info() {
    printf "${BLUE}[INFO] %s${NC}\n" "$1"
}

validate_boolean() {
    local var_name="$1"
    local var_value="$2"
    
    # Convert to lowercase
    local lower_value
    lower_value=$(echo "$var_value" | tr '[:upper:]' '[:lower:]')
    
    case "$lower_value" in
        true|false|1|0|yes|no)
            log_valid "$var_name = $var_value"
            ;;
        "")
            log_warning "$var_name is not set (using default)"
            ;;
        *)
            log_invalid "$var_name = $var_value (expected: true/false)"
            ;;
    esac
}

validate_numeric() {
    local var_name="$1"
    local var_value="$2"
    local min_value="${3:-0}"
    local max_value="${4:-999999}"
    
    if [ -z "$var_value" ]; then
        log_warning "$var_name is not set (using default)"
        return
    fi
    
    # Check if it's a valid number (including decimals)
    if [[ "$var_value" =~ ^-?[0-9]+(\.[0-9]+)?$ ]]; then
        # Use bc for decimal comparison if available, otherwise use integer comparison
        if command -v bc > /dev/null 2>&1; then
            if (( $(echo "$var_value >= $min_value && $var_value <= $max_value" | bc -l) )); then
                log_valid "$var_name = $var_value"
            else
                log_invalid "$var_name = $var_value (expected: $min_value-$max_value)"
            fi
        else
            # Fallback to integer comparison for whole numbers
            local int_value=$(echo "$var_value" | cut -d. -f1)
            if [ "$int_value" -ge "$min_value" ] && [ "$int_value" -le "$max_value" ]; then
                log_valid "$var_name = $var_value"
            else
                log_invalid "$var_name = $var_value (expected: $min_value-$max_value)"
            fi
        fi
    else
        log_invalid "$var_name = $var_value (expected: numeric value)"
    fi
}

validate_path() {
    local var_name="$1"
    local var_value="$2"
    local should_exist="${3:-false}"
    
    if [ -z "$var_value" ]; then
        log_warning "$var_name is not set"
        return
    fi
    
    # Expand relative paths
    if [[ "$var_value" != /* ]]; then
        var_value="$KENNY_ROOT/$var_value"
    fi
    
    if [ "$should_exist" = "true" ]; then
        if [ -e "$var_value" ]; then
            log_valid "$var_name = $var_value (exists)"
        else
            log_invalid "$var_name = $var_value (does not exist)"
        fi
    else
        local dir_path
        dir_path=$(dirname "$var_value")
        if [ -d "$dir_path" ] && [ -w "$dir_path" ]; then
            log_valid "$var_name = $var_value (directory writable)"
        else
            log_invalid "$var_name = $var_value (directory not writable)"
        fi
    fi
}

validate_enum() {
    local var_name="$1"
    local var_value="$2"
    shift 2
    local valid_values=("$@")
    
    if [ -z "$var_value" ]; then
        log_warning "$var_name is not set (using default)"
        return
    fi
    
    for valid_value in "${valid_values[@]}"; do
        if [ "$var_value" = "$valid_value" ]; then
            log_valid "$var_name = $var_value"
            return
        fi
    done
    
    log_invalid "$var_name = $var_value (expected: ${valid_values[*]})"
}

# Display banner
printf "${BLUE}"
cat << "EOF"
 _  __                         ____  _____   ____             __ _       
| |/ /__ _ __  _ __  _   _     |___ \| ____|  / ___|___  _ __  / _(_) __ _ 
| ' // _ \ '_ \| '_ \| | | |     __) |___ \  | |   / _ \| '_ \| |_| |/ _` |
| . \  __/ | | | | | | |_| |   / __/ ___) | | |__| (_) | | | |  _| | (_| |
|_|\_\___|_| |_|_| |_|\__, |  |_____|____/   \____\___/|_| |_|_| |_|\__, |
                     |___/                                         |___/ 
Phase 3.5 Configuration Validation
EOF
printf "${NC}\n"

log_info "Validating Phase 3.5 configuration..."
echo

# Core Configuration
printf "${BLUE}=== Core Configuration ===${NC}\n"
validate_boolean "KENNY_PHASE35_ENABLED" "$KENNY_PHASE35_ENABLED"
validate_enum "KENNY_CALENDAR_PERFORMANCE_MODE" "$KENNY_CALENDAR_PERFORMANCE_MODE" "phase35" "phase32" "auto"
validate_enum "KENNY_PHASE35_EVENTKIT_PERMISSIONS" "$KENNY_PHASE35_EVENTKIT_PERMISSIONS" "auto" "force" "skip"
validate_path "KENNY_DATABASE_PATH" "$KENNY_DATABASE_PATH" false
validate_path "KENNY_PHASE35_DATABASE_PATH" "$KENNY_PHASE35_DATABASE_PATH" false

# Performance Configuration
printf "\n${BLUE}=== Performance Configuration ===${NC}\n"
validate_numeric "KENNY_DB_POOL_SIZE" "$KENNY_DB_POOL_SIZE" 1 100
validate_numeric "KENNY_DB_TIMEOUT" "$KENNY_DB_TIMEOUT" 1 300
validate_numeric "KENNY_DB_CACHE_SIZE" "$KENNY_DB_CACHE_SIZE" -1000000 0
validate_enum "KENNY_DB_JOURNAL_MODE" "$KENNY_DB_JOURNAL_MODE" "WAL" "DELETE" "TRUNCATE" "PERSIST" "MEMORY" "OFF"
validate_enum "KENNY_DB_SYNCHRONOUS" "$KENNY_DB_SYNCHRONOUS" "OFF" "NORMAL" "FULL" "EXTRA"
validate_boolean "KENNY_DB_ENABLE_FTS" "$KENNY_DB_ENABLE_FTS"

# Sync Engine Configuration
printf "\n${BLUE}=== Sync Engine Configuration ===${NC}\n"
validate_boolean "KENNY_SYNC_ENABLED" "$KENNY_SYNC_ENABLED"
validate_numeric "KENNY_SYNC_POLL_INTERVAL" "$KENNY_SYNC_POLL_INTERVAL" 1 3600
validate_numeric "KENNY_SYNC_BATCH_SIZE" "$KENNY_SYNC_BATCH_SIZE" 1 10000
validate_numeric "KENNY_SYNC_RETRY_ATTEMPTS" "$KENNY_SYNC_RETRY_ATTEMPTS" 0 10
validate_numeric "KENNY_SYNC_TIMEOUT" "$KENNY_SYNC_TIMEOUT" 1 300

# EventKit Configuration
printf "\n${BLUE}=== EventKit Configuration ===${NC}\n"
validate_numeric "KENNY_EVENTKIT_POLL_INTERVAL" "$KENNY_EVENTKIT_POLL_INTERVAL" 0 60
validate_numeric "KENNY_EVENTKIT_MAX_EVENTS" "$KENNY_EVENTKIT_MAX_EVENTS" 1 100000
validate_numeric "KENNY_EVENTKIT_SYNC_RANGE_DAYS" "$KENNY_EVENTKIT_SYNC_RANGE_DAYS" 1 3650

# Performance Monitoring
printf "\n${BLUE}=== Performance Monitoring ===${NC}\n"
validate_boolean "KENNY_PERFORMANCE_MONITORING" "$KENNY_PERFORMANCE_MONITORING"
validate_numeric "KENNY_METRICS_INTERVAL" "$KENNY_METRICS_INTERVAL" 1 3600
validate_numeric "KENNY_QUERY_TIME_THRESHOLD" "$KENNY_QUERY_TIME_THRESHOLD" 1 10000

# Logging Configuration
printf "\n${BLUE}=== Logging Configuration ===${NC}\n"
validate_enum "KENNY_PHASE35_LOG_LEVEL" "$KENNY_PHASE35_LOG_LEVEL" "DEBUG" "INFO" "WARNING" "ERROR"
validate_boolean "KENNY_DB_QUERY_LOGGING" "$KENNY_DB_QUERY_LOGGING"
validate_boolean "KENNY_SYNC_LOGGING" "$KENNY_SYNC_LOGGING"

# Fallback Configuration
printf "\n${BLUE}=== Fallback Configuration ===${NC}\n"
validate_boolean "KENNY_AUTO_FALLBACK" "$KENNY_AUTO_FALLBACK"
validate_numeric "KENNY_FALLBACK_RETRY_DELAY" "$KENNY_FALLBACK_RETRY_DELAY" 1 60
validate_numeric "KENNY_FALLBACK_MAX_ATTEMPTS" "$KENNY_FALLBACK_MAX_ATTEMPTS" 1 10

# Cache Configuration
printf "\n${BLUE}=== Cache Configuration ===${NC}\n"
validate_boolean "KENNY_CACHE_L1_ENABLED" "$KENNY_CACHE_L1_ENABLED"
validate_boolean "KENNY_CACHE_L2_ENABLED" "$KENNY_CACHE_L2_ENABLED"
validate_boolean "KENNY_CACHE_L3_ENABLED" "$KENNY_CACHE_L3_ENABLED"
validate_boolean "KENNY_CACHE_L4_ENABLED" "$KENNY_CACHE_L4_ENABLED"
validate_numeric "KENNY_CACHE_L1_SIZE" "$KENNY_CACHE_L1_SIZE" 1 1000
validate_path "KENNY_CACHE_L3_DIR" "$KENNY_CACHE_L3_DIR" false

# Security Configuration
printf "\n${BLUE}=== Security Configuration ===${NC}\n"
validate_boolean "KENNY_DB_ENCRYPTION" "$KENNY_DB_ENCRYPTION"
if [ "$KENNY_DB_ENCRYPTION" = "true" ] && [ -z "$KENNY_DB_ENCRYPTION_KEY" ]; then
    log_invalid "KENNY_DB_ENCRYPTION_KEY is required when encryption is enabled"
elif [ "$KENNY_DB_ENCRYPTION" = "true" ] && [ -n "$KENNY_DB_ENCRYPTION_KEY" ]; then
    log_valid "KENNY_DB_ENCRYPTION_KEY is set (hidden for security)"
fi

# Integration Configuration
printf "\n${BLUE}=== Integration Configuration ===${NC}\n"
validate_enum "KENNY_CALENDAR_BRIDGE_MODE" "$KENNY_CALENDAR_BRIDGE_MODE" "live" "cache" "mock"
validate_boolean "KENNY_INTELLIGENT_CALENDAR_AGENT" "$KENNY_INTELLIGENT_CALENDAR_AGENT"

# Summary
printf "\n${BLUE}=== Validation Summary ===${NC}\n"
echo "Valid configurations: $VALID_COUNT"
echo "Invalid configurations: $INVALID_COUNT"
echo "Warnings: $WARNING_COUNT"

if [ $INVALID_COUNT -eq 0 ]; then
    printf "\n${GREEN}✅ Configuration validation passed!${NC}\n"
    echo "Your Phase 3.5 configuration is valid and ready to use."
    
    if [ $WARNING_COUNT -gt 0 ]; then
        printf "\n${YELLOW}Note: $WARNING_COUNT configuration(s) are using default values.${NC}\n"
        echo "Consider setting these explicitly for better control."
    fi
    
    exit 0
else
    printf "\n${RED}❌ Configuration validation failed!${NC}\n"
    echo "Please fix the $INVALID_COUNT invalid configuration(s) before proceeding."
    echo
    echo "To fix configuration issues:"
    echo "1. Review the .env.phase35 file"
    echo "2. Set missing or invalid environment variables"
    echo "3. Run this script again to validate"
    echo
    echo "Example:"
    echo "  export KENNY_PHASE35_ENABLED=true"
    echo "  export KENNY_CALENDAR_PERFORMANCE_MODE=phase35"
    echo "  ./scripts/validate-phase35-config.sh"
    
    exit 1
fi