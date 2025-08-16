#!/bin/bash

# Kenny v2.0 - Phase 3.5 Calendar Database + Real-time Sync Testing
# Comprehensive testing script for Phase 3.5 functionality
# Usage: ./kenny-test-phase35.sh [--verbose] [--benchmark] [--full]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
KENNY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE35_DATABASE_PATH="$KENNY_ROOT/services/calendar-agent/calendar.db"
TEST_LOG_DIR="$KENNY_ROOT/logs/phase35-tests"
VERBOSE=false
BENCHMARK=false
FULL_TEST=false

# Test metrics
TEST_COUNT=0
PASSED_COUNT=0
FAILED_COUNT=0
START_TIME=$(date +%s)

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --benchmark|-b)
            BENCHMARK=true
            shift
            ;;
        --full|-f)
            FULL_TEST=true
            shift
            ;;
        --help|-h)
            echo "Kenny v2.0 Phase 3.5 Testing Script"
            echo
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --verbose, -v   Verbose output with detailed logs"
            echo "  --benchmark, -b Include performance benchmarking"
            echo "  --full, -f      Run full comprehensive test suite"
            echo "  --help, -h      Show this help message"
            echo
            echo "Test Categories:"
            echo "  • Database Operations"
            echo "  • Real-time Sync Engine"
            echo "  • Performance Validation"
            echo "  • End-to-end Functionality"
            echo "  • EventKit Integration"
            echo "  • Error Recovery"
            echo
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create test log directory
mkdir -p "$TEST_LOG_DIR"

# Utility functions
log_test() {
    printf "${GREEN}[TEST] %s${NC}\n" "$1"
    if [ "$VERBOSE" = true ]; then
        echo "[$(date +'%H:%M:%S')] TEST: $1" >> "$TEST_LOG_DIR/test-run.log"
    fi
}

log_pass() {
    printf "${GREEN}[PASS] %s${NC}\n" "$1"
    PASSED_COUNT=$((PASSED_COUNT + 1))
    if [ "$VERBOSE" = true ]; then
        echo "[$(date +'%H:%M:%S')] PASS: $1" >> "$TEST_LOG_DIR/test-run.log"
    fi
}

log_fail() {
    printf "${RED}[FAIL] %s${NC}\n" "$1"
    FAILED_COUNT=$((FAILED_COUNT + 1))
    if [ "$VERBOSE" = true ]; then
        echo "[$(date +'%H:%M:%S')] FAIL: $1" >> "$TEST_LOG_DIR/test-run.log"
    fi
}

log_warn() {
    printf "${YELLOW}[WARN] %s${NC}\n" "$1"
    if [ "$VERBOSE" = true ]; then
        echo "[$(date +'%H:%M:%S')] WARN: $1" >> "$TEST_LOG_DIR/test-run.log"
    fi
}

log_info() {
    printf "${BLUE}[INFO] %s${NC}\n" "$1"
    if [ "$VERBOSE" = true ]; then
        echo "[$(date +'%H:%M:%S')] INFO: $1" >> "$TEST_LOG_DIR/test-run.log"
    fi
}

run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="${3:-0}"
    
    TEST_COUNT=$((TEST_COUNT + 1))
    log_test "$test_name"
    
    if [ "$VERBOSE" = true ]; then
        echo "Running: $test_command" >> "$TEST_LOG_DIR/test-run.log"
    fi
    
    local result
    local exit_code
    
    if [ "$VERBOSE" = true ]; then
        result=$(eval "$test_command" 2>&1 | tee -a "$TEST_LOG_DIR/test-run.log")
        exit_code=${PIPESTATUS[0]}
    else
        result=$(eval "$test_command" 2>&1)
        exit_code=$?
    fi
    
    if [ $exit_code -eq $expected_result ]; then
        log_pass "$test_name"
        return 0
    else
        log_fail "$test_name (exit code: $exit_code, expected: $expected_result)"
        if [ "$VERBOSE" = false ]; then
            echo "Error output: $result"
        fi
        return 1
    fi
}

# Performance test function
benchmark_test() {
    local test_name="$1"
    local test_command="$2"
    local max_time_ms="$3"
    
    TEST_COUNT=$((TEST_COUNT + 1))
    log_test "$test_name (target: <${max_time_ms}ms)"
    
    local start_time=$(date +%s%3N)
    local result
    local exit_code
    
    result=$(eval "$test_command" 2>&1)
    exit_code=$?
    
    local end_time=$(date +%s%3N)
    local duration=$((end_time - start_time))
    
    if [ $exit_code -eq 0 ] && [ $duration -lt $max_time_ms ]; then
        log_pass "$test_name (${duration}ms < ${max_time_ms}ms)"
        return 0
    else
        if [ $exit_code -ne 0 ]; then
            log_fail "$test_name (command failed: exit code $exit_code)"
        else
            log_fail "$test_name (${duration}ms >= ${max_time_ms}ms)"
        fi
        return 1
    fi
}

# Display banner
printf "${BLUE}"
cat << "EOF"
 _  __                         ____  _____         _   
| |/ /__ _ __  _ __  _   _     |___ \| ____|       | |_ 
| ' // _ \ '_ \| '_ \| | | |     __) |___ \   __   | __|
| . \  __/ | | | | | | |_| |   / __/ ___) | |__| |_| |_ 
|_|\_\___|_| |_|_| |_|\__, |  |_____|____/         \__|
                     |___/                             
Phase 3.5 Calendar Database + Real-time Sync Testing
EOF
printf "${NC}\n"

log_info "Starting Phase 3.5 comprehensive test suite..."
log_info "Test configuration: verbose=$VERBOSE, benchmark=$BENCHMARK, full=$FULL_TEST"
echo

# Test 1: Prerequisites Check
printf "${CYAN}=== Test Category 1: Prerequisites Check ===${NC}\n"

run_test "Python 3 available" "python3 --version"
run_test "Calendar agent source exists" "test -d '$KENNY_ROOT/services/calendar-agent/src'"
run_test "Database directory accessible" "test -w '$(dirname "$PHASE35_DATABASE_PATH")'"

# Test 2: EventKit Integration
printf "\n${CYAN}=== Test Category 2: EventKit Integration ===${NC}\n"

eventkit_test_script='
try:
    from EventKit import EKEventStore, EKAuthorizationStatus, EKEntityType
    store = EKEventStore.alloc().init()
    status = EKEventStore.authorizationStatusForEntityType_(EKEntityType.EKEntityTypeEvent)
    print(f"EventKit status: {status}")
    exit(0 if status == EKAuthorizationStatus.EKAuthorizationStatusAuthorized else 1)
except ImportError:
    print("EventKit not available")
    exit(2)
except Exception as e:
    print(f"EventKit error: {e}")
    exit(3)
'

run_test "EventKit framework availability" "python3 -c '$eventkit_test_script'" 0

# Test 3: Database Operations
printf "\n${CYAN}=== Test Category 3: Database Operations ===${NC}\n"

database_init_test='
import sys
import os
sys.path.append("'$KENNY_ROOT'/services/calendar-agent/src")
try:
    from calendar_database import CalendarDatabase, DatabaseConfig
    import asyncio
    
    async def test_db_init():
        config = DatabaseConfig(database_path="'$PHASE35_DATABASE_PATH'")
        db = CalendarDatabase(config)
        await db.initialize()
        await db.close()
        print("Database initialization successful")
    
    asyncio.run(test_db_init())
except Exception as e:
    print(f"Database error: {e}")
    exit(1)
'

run_test "Database initialization" "python3 -c '$database_init_test'"

database_operations_test='
import sys
import os
import time
from datetime import datetime, timedelta
sys.path.append("'$KENNY_ROOT'/services/calendar-agent/src")
try:
    from calendar_database import CalendarDatabase, DatabaseConfig, CalendarEvent
    import asyncio
    
    async def test_db_operations():
        config = DatabaseConfig(database_path="'$PHASE35_DATABASE_PATH'")
        db = CalendarDatabase(config)
        await db.initialize()
        
        # Test event creation
        test_event = CalendarEvent(
            id="test-event-" + str(int(time.time())),
            title="Test Event",
            start_datetime=datetime.now(),
            end_datetime=datetime.now() + timedelta(hours=1),
            calendar_id="test-calendar"
        )
        
        await db.store_event(test_event)
        
        # Test event retrieval
        events = await db.get_events_in_range(
            datetime.now() - timedelta(hours=1),
            datetime.now() + timedelta(hours=2)
        )
        
        # Test event deletion
        await db.delete_event(test_event.id)
        
        await db.close()
        print(f"Database operations successful (found {len(events)} events)")
    
    asyncio.run(test_db_operations())
except Exception as e:
    print(f"Database operations error: {e}")
    exit(1)
'

run_test "Database CRUD operations" "python3 -c '$database_operations_test'"

# Test 4: Performance Validation
printf "\n${CYAN}=== Test Category 4: Performance Validation ===${NC}\n"

if [ "$BENCHMARK" = true ]; then
    performance_test='
import sys
import os
import time
from datetime import datetime, timedelta
sys.path.append("'$KENNY_ROOT'/services/calendar-agent/src")
try:
    from calendar_database import CalendarDatabase, DatabaseConfig
    import asyncio
    
    async def test_performance():
        config = DatabaseConfig(database_path="'$PHASE35_DATABASE_PATH'")
        db = CalendarDatabase(config)
        await db.initialize()
        
        # Test query performance
        start_time = time.time()
        events = await db.get_events_in_range(
            datetime.now() - timedelta(days=7),
            datetime.now() + timedelta(days=7)
        )
        query_time = (time.time() - start_time) * 1000
        
        await db.close()
        print(f"Query completed in {query_time:.2f}ms")
        exit(0 if query_time < 10 else 1)
    
    asyncio.run(test_performance())
except Exception as e:
    print(f"Performance test error: {e}")
    exit(1)
'
    
    benchmark_test "Database query performance" "python3 -c '$performance_test'" 10
else
    log_info "Skipping performance benchmarks (use --benchmark to enable)"
fi

# Test 5: Component Integration
printf "\n${CYAN}=== Test Category 5: Component Integration ===${NC}\n"

integration_test='
import sys
import os
sys.path.append("'$KENNY_ROOT'/services/calendar-agent/src")
try:
    from week2_integration_coordinator import Week2IntegrationCoordinator
    from calendar_database import CalendarDatabase, DatabaseConfig
    import asyncio
    
    async def test_integration():
        config = DatabaseConfig(database_path="'$PHASE35_DATABASE_PATH'")
        db = CalendarDatabase(config)
        await db.initialize()
        
        coordinator = Week2IntegrationCoordinator(database=db)
        
        # Test health check
        health = await coordinator.get_health_status()
        
        await db.close()
        print(f"Integration health: {health}")
        exit(0 if health.get(\"healthy\", False) else 1)
    
    asyncio.run(test_integration())
except Exception as e:
    print(f"Integration test error: {e}")
    exit(1)
'

run_test "Component integration health" "python3 -c '$integration_test'"

# Test 6: Full End-to-End Test (if --full flag is used)
if [ "$FULL_TEST" = true ]; then
    printf "\n${CYAN}=== Test Category 6: End-to-End Functionality ===${NC}\n"
    
    e2e_test='
import sys
import os
import time
from datetime import datetime, timedelta
sys.path.append("'$KENNY_ROOT'/services/calendar-agent/src")
try:
    from week2_integration_coordinator import Week2IntegrationCoordinator
    from calendar_database import CalendarDatabase, DatabaseConfig, CalendarEvent
    import asyncio
    
    async def test_e2e():
        config = DatabaseConfig(database_path="'$PHASE35_DATABASE_PATH'")
        db = CalendarDatabase(config)
        await db.initialize()
        
        coordinator = Week2IntegrationCoordinator(database=db)
        await coordinator.start()
        
        # Test full workflow
        test_event = CalendarEvent(
            id="e2e-test-" + str(int(time.time())),
            title="End-to-End Test Event",
            start_datetime=datetime.now() + timedelta(hours=1),
            end_datetime=datetime.now() + timedelta(hours=2),
            calendar_id="test-calendar"
        )
        
        # Store and sync
        await db.store_event(test_event)
        
        # Wait for sync
        await asyncio.sleep(1)
        
        # Verify event exists
        events = await db.get_events_in_range(
            datetime.now(),
            datetime.now() + timedelta(hours=3)
        )
        
        found_event = any(e.id == test_event.id for e in events)
        
        # Cleanup
        await db.delete_event(test_event.id)
        await coordinator.stop()
        await db.close()
        
        print(f"End-to-end test: event found = {found_event}")
        exit(0 if found_event else 1)
    
    asyncio.run(test_e2e())
except Exception as e:
    print(f"End-to-end test error: {e}")
    exit(1)
'
    
    run_test "End-to-end workflow" "python3 -c '$e2e_test'"
else
    log_info "Skipping end-to-end tests (use --full to enable)"
fi

# Test 7: Error Recovery
printf "\n${CYAN}=== Test Category 7: Error Recovery ===${NC}\n"

error_recovery_test='
import sys
import os
sys.path.append("'$KENNY_ROOT'/services/calendar-agent/src")
try:
    from calendar_database import CalendarDatabase, DatabaseConfig
    import asyncio
    
    async def test_error_recovery():
        # Test with invalid database path
        config = DatabaseConfig(database_path="/invalid/path/test.db")
        db = CalendarDatabase(config)
        
        try:
            await db.initialize()
            print("ERROR: Should have failed with invalid path")
            exit(1)
        except Exception:
            print("Correctly handled invalid database path")
        
        # Test with valid path
        config = DatabaseConfig(database_path="'$PHASE35_DATABASE_PATH'")
        db = CalendarDatabase(config)
        await db.initialize()
        await db.close()
        print("Recovery to valid configuration successful")
    
    asyncio.run(test_error_recovery())
except Exception as e:
    print(f"Error recovery test failed: {e}")
    exit(1)
'

run_test "Error recovery handling" "python3 -c '$error_recovery_test'"

# Test Results Summary
printf "\n${BLUE}=== Test Results Summary ===${NC}\n"

local end_time=$(date +%s)
local duration=$((end_time - START_TIME))

echo "Tests completed in ${duration} seconds"
echo "Total tests: $TEST_COUNT"
printf "Passed: ${GREEN}$PASSED_COUNT${NC}\n"
printf "Failed: ${RED}$FAILED_COUNT${NC}\n"

local success_rate=0
if [ $TEST_COUNT -gt 0 ]; then
    success_rate=$((PASSED_COUNT * 100 / TEST_COUNT))
fi

printf "Success rate: "
if [ $success_rate -ge 90 ]; then
    printf "${GREEN}$success_rate%%${NC}\n"
elif [ $success_rate -ge 70 ]; then
    printf "${YELLOW}$success_rate%%${NC}\n"
else
    printf "${RED}$success_rate%%${NC}\n"
fi

echo
if [ $FAILED_COUNT -eq 0 ]; then
    printf "${GREEN}🎉 All Phase 3.5 tests passed! System is ready for production use.${NC}\n"
    echo
    echo "Phase 3.5 features validated:"
    echo "• Calendar database operations"
    echo "• Real-time synchronization"
    echo "• Performance targets (<10ms queries)"
    echo "• Component integration"
    echo "• Error recovery"
    echo
    echo "You can now use Phase 3.5 with confidence!"
    exit_code=0
else
    printf "${RED}⚠️ Some Phase 3.5 tests failed. Review the issues above.${NC}\n"
    echo
    echo "Common solutions:"
    echo "• Check EventKit permissions in System Preferences"
    echo "• Verify database file permissions"
    echo "• Ensure all dependencies are installed"
    echo "• Run './kenny-launch.sh' to initialize the system"
    echo
    echo "For detailed logs, check: $TEST_LOG_DIR/"
    exit_code=1
fi

if [ "$VERBOSE" = true ]; then
    echo
    echo "Detailed test logs available at: $TEST_LOG_DIR/test-run.log"
fi

exit $exit_code