# Kenny v2.0 Phase 3.5 Calendar Database + Real-time Sync

This document provides comprehensive instructions for using Kenny's Phase 3.5 Calendar Database + Real-time Sync functionality.

## Overview

Phase 3.5 introduces a high-performance calendar database with real-time bidirectional synchronization, targeting <0.01s query performance and seamless EventKit integration.

### Key Features

- **High-Performance Database**: SQLite-based calendar database with optimized indexing
- **Real-time Sync**: Bidirectional synchronization with macOS Calendar via EventKit
- **Performance Monitoring**: Sub-10ms query performance validation
- **Automatic Fallback**: Graceful degradation to Phase 3.2 if Phase 3.5 fails
- **Comprehensive Testing**: Built-in validation and benchmarking tools

## Quick Start

### 1. Enable Phase 3.5

```bash
# Option A: Use the provided configuration file
source .env.phase35

# Option B: Set environment variables manually
export KENNY_PHASE35_ENABLED=true
export KENNY_CALENDAR_PERFORMANCE_MODE=phase35
export KENNY_PHASE35_EVENTKIT_PERMISSIONS=auto
```

### 2. Launch Kenny with Phase 3.5

```bash
./kenny-launch.sh
```

The launch script will:
- Load Phase 3.5 configuration
- Check EventKit permissions (prompt if needed)
- Initialize the high-performance database
- Validate component integration
- Enable Phase 3.5 mode or fallback to Phase 3.2

### 3. Verify Phase 3.5 Status

```bash
# Check general status
./kenny-status.sh

# Check Phase 3.5 specific status
./kenny-status.sh --phase35
```

### 4. Test Phase 3.5 Functionality

```bash
# Basic functionality test
./kenny-test-phase35.sh

# Verbose testing with benchmarks
./kenny-test-phase35.sh --verbose --benchmark

# Full comprehensive test suite
./kenny-test-phase35.sh --full --verbose --benchmark
```

## Configuration

### Environment Variables

Phase 3.5 can be configured using environment variables. The provided `.env.phase35` file contains all available options with documentation.

#### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `KENNY_PHASE35_ENABLED` | `true` | Enable Phase 3.5 features |
| `KENNY_CALENDAR_PERFORMANCE_MODE` | `phase35` | Performance mode (phase35/phase32) |
| `KENNY_PHASE35_EVENTKIT_PERMISSIONS` | `auto` | EventKit permission handling (auto/force/skip) |
| `KENNY_DATABASE_PATH` | `services/calendar-agent/calendar.db` | Database file path |

#### Performance Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `KENNY_DB_POOL_SIZE` | `10` | Database connection pool size |
| `KENNY_DB_CACHE_SIZE` | `-64000` | Database cache size (64MB) |
| `KENNY_QUERY_TIME_THRESHOLD` | `10` | Query time threshold (ms) |
| `KENNY_SYNC_POLL_INTERVAL` | `1` | Sync polling interval (seconds) |

### Configuration Validation

Validate your configuration before launching:

```bash
./scripts/validate-phase35-config.sh
```

This will check all environment variables and provide recommendations.

## Performance Targets

Phase 3.5 is designed to meet these performance criteria:

- **Query Performance**: <10ms for typical calendar queries
- **Sync Latency**: <1s end-to-end synchronization
- **CPU Usage**: <5% during normal operation
- **Memory Usage**: <100MB additional overhead
- **Change Detection**: <100ms EventKit change detection

## EventKit Integration

### Permission Requirements

Phase 3.5 requires Calendar permissions to function:

1. On first launch, macOS will prompt for Calendar access
2. Grant "Full Access" when prompted
3. Permissions can be managed in System Preferences > Security & Privacy > Privacy > Calendars

### Permission Troubleshooting

If EventKit permissions are denied:

```bash
# Check current permission status
./kenny-status.sh --phase35

# Reset permissions (will re-prompt)
tccutil reset Calendar com.apple.Terminal
./kenny-launch.sh
```

## Fallback Behavior

Phase 3.5 includes automatic fallback to Phase 3.2 in these scenarios:

- EventKit permissions denied
- Database initialization fails
- Component integration fails
- Performance targets not met

Fallback is automatic and transparent to users.

## Scripts Reference

### kenny-launch.sh

Enhanced launch script with Phase 3.5 support:

```bash
# Standard launch
./kenny-launch.sh

# With custom configuration
export KENNY_PHASE35_ENABLED=true
./kenny-launch.sh
```

**New Features:**
- Phase 3.5 configuration loading
- EventKit permission checking
- Database initialization
- Component validation
- Performance mode reporting

### kenny-status.sh

Status monitoring with Phase 3.5 metrics:

```bash
# General status (includes Phase 3.5 summary)
./kenny-status.sh

# Phase 3.5 detailed status
./kenny-status.sh --phase35

# Continuous monitoring
./kenny-status.sh --watch
```

**Phase 3.5 Status Includes:**
- Database file size and health
- EventKit permission status
- Query performance metrics
- Sync engine status
- Cache layer coordination

### kenny-test-phase35.sh

Comprehensive testing suite:

```bash
# Basic functionality test
./kenny-test-phase35.sh

# Include performance benchmarks
./kenny-test-phase35.sh --benchmark

# Full test suite with verbose output
./kenny-test-phase35.sh --full --verbose
```

**Test Categories:**
1. Prerequisites Check
2. EventKit Integration
3. Database Operations
4. Performance Validation
5. Component Integration
6. End-to-End Functionality
7. Error Recovery

### validate-phase35-config.sh

Configuration validation tool:

```bash
# Validate current environment
./scripts/validate-phase35-config.sh

# Validate with config file
source .env.phase35
./scripts/validate-phase35-config.sh
```

## Troubleshooting

### Common Issues

#### 1. EventKit Permissions Denied

**Symptoms:** Phase 3.5 falls back to Phase 3.2, EventKit status shows "DENIED"

**Solution:**
```bash
# Reset and re-request permissions
tccutil reset Calendar com.apple.Terminal
./kenny-launch.sh
```

#### 2. Database Initialization Fails

**Symptoms:** Database file not created, initialization errors in logs

**Solution:**
```bash
# Check directory permissions
ls -la services/calendar-agent/
chmod 755 services/calendar-agent/

# Remove corrupted database
rm -f services/calendar-agent/calendar.db
./kenny-launch.sh
```

#### 3. Poor Query Performance

**Symptoms:** Query times >10ms, performance warnings

**Solution:**
```bash
# Check database health
./kenny-status.sh --phase35

# Run performance benchmark
./kenny-test-phase35.sh --benchmark

# Rebuild database with optimizations
export KENNY_DB_CACHE_SIZE=-128000
./kenny-launch.sh
```

#### 4. Sync Engine Not Working

**Symptoms:** Changes not synchronized, sync status "stopped"

**Solution:**
```bash
# Check EventKit permissions
./kenny-status.sh --phase35

# Restart sync engine
export KENNY_SYNC_ENABLED=true
./kenny-launch.sh
```

### Debug Mode

Enable detailed debugging:

```bash
export KENNY_DEBUG_MODE=true
export KENNY_PHASE35_LOG_LEVEL=DEBUG
export KENNY_DB_QUERY_LOGGING=true
./kenny-launch.sh
```

Debug logs will be available in `logs/` directory.

### Performance Monitoring

Monitor Phase 3.5 performance:

```bash
# Real-time performance metrics
./kenny-status.sh --watch

# Performance benchmarking
./kenny-test-phase35.sh --benchmark --verbose

# Query performance analysis
tail -f logs/calendar-agent.log | grep "QUERY_TIME"
```

## Migration from Phase 3.2

Phase 3.5 is backward compatible with Phase 3.2. No data migration is required.

To migrate:

1. **Backup existing data** (optional):
   ```bash
   cp -r services/calendar-agent/ services/calendar-agent.backup/
   ```

2. **Enable Phase 3.5**:
   ```bash
   source .env.phase35
   ./kenny-launch.sh
   ```

3. **Verify functionality**:
   ```bash
   ./kenny-test-phase35.sh
   ```

4. **Monitor performance**:
   ```bash
   ./kenny-status.sh --phase35
   ```

## Advanced Configuration

### High-Performance Setup

For maximum performance:

```bash
export KENNY_DB_CACHE_SIZE=-128000        # 128MB cache
export KENNY_DB_POOL_SIZE=20              # More connections
export KENNY_SYNC_POLL_INTERVAL=0.5       # Faster sync
export KENNY_EVENTKIT_POLL_INTERVAL=0.05  # Ultra-fast detection
export KENNY_CACHE_L1_SIZE=100            # Larger L1 cache
```

### Development Setup

For development and testing:

```bash
export KENNY_TEST_MODE=true
export KENNY_DEBUG_MODE=true
export KENNY_MOCK_EVENTKIT=true
export KENNY_DB_QUERY_LOGGING=true
export KENNY_PHASE35_LOG_LEVEL=DEBUG
```

### Production Setup

For production deployment:

```bash
export KENNY_PHASE35_LOG_LEVEL=WARNING
export KENNY_DB_QUERY_LOGGING=false
export KENNY_AUTO_FALLBACK=true
export KENNY_DB_BACKUP_ENABLED=true
export KENNY_PERFORMANCE_MONITORING=true
```

## Support

For issues or questions:

1. **Check logs**: `logs/calendar-agent.log`
2. **Run diagnostics**: `./kenny-test-phase35.sh --full --verbose`
3. **Validate config**: `./scripts/validate-phase35-config.sh`
4. **Check status**: `./kenny-status.sh --phase35`

## Version History

- **Phase 3.5.0**: Initial release with high-performance database and real-time sync
- **Phase 3.2.x**: Previous version with basic calendar functionality (still available as fallback)

---

*This document covers Kenny v2.0 Phase 3.5 Calendar Database + Real-time Sync functionality. For general Kenny documentation, see the main README files.*