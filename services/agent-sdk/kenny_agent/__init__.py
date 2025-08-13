"""
Kenny Agent SDK - Base framework for building agents in the Kenny v2 system.

This package provides the foundational classes and utilities for creating
agents that can register with the agent registry and execute capabilities.
"""

from .base_agent import BaseAgent
from .base_handler import BaseCapabilityHandler
from .base_tool import BaseTool
from .health import HealthStatus, HealthCheck, HealthMonitor
from .registry import AgentRegistryClient

__version__ = "0.1.0"
__all__ = [
    "BaseAgent",
    "BaseCapabilityHandler", 
    "BaseTool",
    "HealthStatus",
    "HealthCheck",
    "HealthMonitor",
    "AgentRegistryClient"
]
