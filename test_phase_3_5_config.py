#!/usr/bin/env python3
"""
Configuration Management for Phase 3.5 Calendar Database Test Framework

This module provides centralized configuration management for all test scenarios,
environments, and parameters used in the Phase 3.5 testing framework.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path


@dataclass
class DatabaseTestConfig:
    """Configuration for database testing."""
    test_database_path: str = ":memory:"
    connection_pool_size: int = 10
    connection_timeout: float = 30.0
    query_timeout: float = 10.0
    enable_foreign_keys: bool = True
    enable_wal_mode: bool = True
    cache_size: int = 2000
    temp_store: str = "memory"
    synchronous_mode: str = "NORMAL"
    journal_mode: str = "WAL"


@dataclass
class PerformanceTestConfig:
    """Configuration for performance testing."""
    target_response_time: float = 5.0
    baseline_response_time: float = 17.5  # Phase 3.2 average
    performance_improvement_target: float = 0.70  # 70% improvement
    load_test_duration: int = 60
    max_concurrent_users: int = 50
    ramp_up_time: int = 10
    operation_timeout: float = 30.0
    memory_limit_mb: int = 512
    cpu_limit_percent: float = 80.0


@dataclass
class SyncTestConfig:
    """Configuration for synchronization testing."""
    sync_test_iterations: int = 100
    conflict_resolution_timeout: float = 5.0
    sync_batch_size: int = 50
    max_retry_attempts: int = 3
    retry_backoff_multiplier: float = 2.0
    bidirectional_test_cycles: int = 10
    event_change_detection_latency: float = 1.0
    sync_accuracy_threshold: float = 0.99


@dataclass
class SecurityTestConfig:
    """Configuration for security testing."""
    encryption_algorithm: str = "AES-256"
    key_rotation_interval: int = 86400  # 24 hours
    access_control_tests: List[str] = field(default_factory=lambda: [
        "file_permissions", "process_isolation", "network_isolation",
        "data_sanitization", "audit_logging"
    ])
    vulnerability_scan_enabled: bool = True
    compliance_standards: List[str] = field(default_factory=lambda: [
        "GDPR", "CCPA", "SOC2"
    ])


@dataclass
class IntegrationTestConfig:
    """Configuration for Phase 3.2 integration testing."""
    cache_integration_enabled: bool = True
    l1_cache_size: int = 1000
    l2_redis_host: str = "localhost"
    l2_redis_port: int = 6379
    l2_redis_db: int = 1
    l3_prediction_enabled: bool = True
    parallel_processing_enabled: bool = True
    max_parallel_operations: int = 20
    cache_warming_interval: int = 3600


@dataclass
class MockDataConfig:
    """Configuration for mock data generation."""
    default_events_count: int = 100
    default_calendars_count: int = 5
    default_contacts_count: int = 50
    event_duration_range: tuple = (30, 240)  # minutes
    future_time_range: tuple = (1, 7200)  # seconds
    all_day_event_probability: float = 0.1
    recurring_event_probability: float = 0.2
    location_probability: float = 0.7
    url_probability: float = 0.3


@dataclass
class TestEnvironmentConfig:
    """Configuration for test environment."""
    test_data_directory: str = "test_data"
    log_directory: str = "logs"
    report_directory: str = "test_reports"
    temp_directory: str = "temp"
    cleanup_on_exit: bool = True
    preserve_failed_test_data: bool = True
    enable_debug_logging: bool = False
    log_level: str = "INFO"
    max_log_file_size: int = 10485760  # 10MB
    log_rotation_count: int = 5


@dataclass
class Phase35TestFrameworkConfig:
    """Master configuration for Phase 3.5 test framework."""
    
    # Component configurations
    database: DatabaseTestConfig = field(default_factory=DatabaseTestConfig)
    performance: PerformanceTestConfig = field(default_factory=PerformanceTestConfig)
    sync: SyncTestConfig = field(default_factory=SyncTestConfig)
    security: SecurityTestConfig = field(default_factory=SecurityTestConfig)
    integration: IntegrationTestConfig = field(default_factory=IntegrationTestConfig)
    mock_data: MockDataConfig = field(default_factory=MockDataConfig)
    environment: TestEnvironmentConfig = field(default_factory=TestEnvironmentConfig)
    
    # Global test settings
    test_suite_timeout: float = 1800.0  # 30 minutes
    parallel_test_execution: bool = False  # Sequential by default for reliability
    fail_fast: bool = False
    generate_coverage_report: bool = True
    generate_performance_report: bool = True
    generate_security_report: bool = True
    
    # Test selection
    skip_load_tests: bool = False
    skip_security_tests: bool = False
    skip_integration_tests: bool = False
    only_smoke_tests: bool = False
    
    # Notification settings
    notify_on_completion: bool = False
    notify_on_failure: bool = True
    notification_email: Optional[str] = None
    slack_webhook: Optional[str] = None


class TestConfigurationManager:
    """Manages test configuration and environment setup."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_file = config_file
        self.config = Phase35TestFrameworkConfig()
        
        # Load configuration from environment and files
        self._load_from_environment()
        if config_file:
            self._load_from_file(config_file)
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        
        # Database configuration
        if os.getenv("TEST_DATABASE_PATH"):
            self.config.database.test_database_path = os.getenv("TEST_DATABASE_PATH")
        
        # Performance configuration
        if os.getenv("PERFORMANCE_TARGET"):
            self.config.performance.target_response_time = float(os.getenv("PERFORMANCE_TARGET"))
        
        if os.getenv("LOAD_TEST_DURATION"):
            self.config.performance.load_test_duration = int(os.getenv("LOAD_TEST_DURATION"))
        
        if os.getenv("MAX_CONCURRENT_USERS"):
            self.config.performance.max_concurrent_users = int(os.getenv("MAX_CONCURRENT_USERS"))
        
        # Sync configuration
        if os.getenv("SYNC_TEST_ITERATIONS"):
            self.config.sync.sync_test_iterations = int(os.getenv("SYNC_TEST_ITERATIONS"))
        
        # Integration configuration
        if os.getenv("REDIS_HOST"):
            self.config.integration.l2_redis_host = os.getenv("REDIS_HOST")
        
        if os.getenv("REDIS_PORT"):
            self.config.integration.l2_redis_port = int(os.getenv("REDIS_PORT"))
        
        # Global settings
        if os.getenv("SKIP_LOAD_TESTS"):
            self.config.skip_load_tests = os.getenv("SKIP_LOAD_TESTS").lower() == "true"
        
        if os.getenv("SKIP_SECURITY_TESTS"):
            self.config.skip_security_tests = os.getenv("SKIP_SECURITY_TESTS").lower() == "true"
        
        if os.getenv("ONLY_SMOKE_TESTS"):
            self.config.only_smoke_tests = os.getenv("ONLY_SMOKE_TESTS").lower() == "true"
        
        if os.getenv("FAIL_FAST"):
            self.config.fail_fast = os.getenv("FAIL_FAST").lower() == "true"
    
    def _load_from_file(self, config_file: str):
        """Load configuration from YAML or JSON file."""
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        # Implementation would parse YAML/JSON and update config
        # For now, we'll use environment variables and defaults
        pass
    
    def get_test_config(self, test_type: str) -> Dict[str, Any]:
        """Get configuration for specific test type."""
        test_configs = {
            "database": self.config.database,
            "performance": self.config.performance,
            "sync": self.config.sync,
            "security": self.config.security,
            "integration": self.config.integration,
            "mock_data": self.config.mock_data,
            "environment": self.config.environment
        }
        
        return test_configs.get(test_type, self.config)
    
    def should_run_test(self, test_name: str) -> bool:
        """Determine if a specific test should be run based on configuration."""
        
        if self.config.only_smoke_tests:
            smoke_tests = [
                "database_query_performance",
                "crud_operation_performance",
                "data_consistency_validation",
                "bidirectional_sync_accuracy"
            ]
            return test_name in smoke_tests
        
        if self.config.skip_load_tests and "load" in test_name.lower():
            return False
        
        if self.config.skip_security_tests and "security" in test_name.lower():
            return False
        
        if self.config.skip_integration_tests and "integration" in test_name.lower():
            return False
        
        return True
    
    def setup_test_directories(self):
        """Set up required test directories."""
        directories = [
            self.config.environment.test_data_directory,
            self.config.environment.log_directory,
            self.config.environment.report_directory,
            self.config.environment.temp_directory
        ]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
    
    def get_database_url(self) -> str:
        """Get the database URL for testing."""
        return self.config.database.test_database_path
    
    def get_redis_url(self) -> str:
        """Get the Redis URL for integration testing."""
        return f"redis://{self.config.integration.l2_redis_host}:{self.config.integration.l2_redis_port}/{self.config.integration.l2_redis_db}"
    
    def export_config(self) -> Dict[str, Any]:
        """Export current configuration as dictionary."""
        return {
            "database": self.config.database.__dict__,
            "performance": self.config.performance.__dict__,
            "sync": self.config.sync.__dict__,
            "security": self.config.security.__dict__,
            "integration": self.config.integration.__dict__,
            "mock_data": self.config.mock_data.__dict__,
            "environment": self.config.environment.__dict__,
            "global_settings": {
                "test_suite_timeout": self.config.test_suite_timeout,
                "parallel_test_execution": self.config.parallel_test_execution,
                "fail_fast": self.config.fail_fast,
                "skip_load_tests": self.config.skip_load_tests,
                "skip_security_tests": self.config.skip_security_tests,
                "skip_integration_tests": self.config.skip_integration_tests,
                "only_smoke_tests": self.config.only_smoke_tests
            }
        }


# Predefined configuration presets
DEVELOPMENT_CONFIG = Phase35TestFrameworkConfig(
    performance=PerformanceTestConfig(
        load_test_duration=30,
        max_concurrent_users=10
    ),
    sync=SyncTestConfig(
        sync_test_iterations=20
    ),
    mock_data=MockDataConfig(
        default_events_count=50,
        default_calendars_count=3,
        default_contacts_count=20
    ),
    skip_load_tests=True,
    only_smoke_tests=True
)

CI_CONFIG = Phase35TestFrameworkConfig(
    performance=PerformanceTestConfig(
        load_test_duration=60,
        max_concurrent_users=20
    ),
    sync=SyncTestConfig(
        sync_test_iterations=50
    ),
    security=SecurityTestConfig(
        vulnerability_scan_enabled=False  # Skip intensive scans in CI
    ),
    fail_fast=True,
    parallel_test_execution=False
)

PRODUCTION_VALIDATION_CONFIG = Phase35TestFrameworkConfig(
    performance=PerformanceTestConfig(
        load_test_duration=300,  # 5 minutes
        max_concurrent_users=100
    ),
    sync=SyncTestConfig(
        sync_test_iterations=200
    ),
    mock_data=MockDataConfig(
        default_events_count=500,
        default_calendars_count=10,
        default_contacts_count=200
    ),
    generate_coverage_report=True,
    generate_performance_report=True,
    generate_security_report=True
)


def get_config_preset(preset_name: str) -> Phase35TestFrameworkConfig:
    """Get a predefined configuration preset."""
    presets = {
        "development": DEVELOPMENT_CONFIG,
        "ci": CI_CONFIG,
        "production": PRODUCTION_VALIDATION_CONFIG
    }
    
    return presets.get(preset_name.lower(), Phase35TestFrameworkConfig())