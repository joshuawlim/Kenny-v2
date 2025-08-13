"""
Base Tool class for the Kenny v2 multi-agent system.

This class provides the foundation for implementing tools that agents
can use to perform specific operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


class BaseTool(ABC):
    """
    Base class for implementing agent tools.
    
    Tools provide specific functionality that agents can use, such as
    database access, file operations, or external API calls.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        category: str = "general"
    ):
        """
        Initialize the tool.
        
        Args:
            name: Unique name for the tool
            description: Human-readable description of the tool
            version: Version string for the tool
            input_schema: JSON Schema for input parameters
            output_schema: JSON Schema for return values
            category: Category of the tool (e.g., 'database', 'file', 'api')
        """
        self.name = name
        self.description = description
        self.version = version
        self.input_schema = input_schema or {}
        self.output_schema = output_schema or {}
        self.category = category
        
        # Tool metadata
        self.created_at = None
        self.last_used = None
        self.usage_count = 0
    
    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> Any:
        """
        Execute the tool with the given parameters.
        
        This method must be implemented by subclasses to provide
        the actual tool functionality.
        
        Args:
            parameters: Input parameters for the tool
            
        Returns:
            Result of the tool execution
            
        Raises:
            Exception: If the tool execution fails
        """
        raise NotImplementedError("Subclasses must implement execute method")
    
    def get_manifest(self) -> Dict[str, Any]:
        """
        Generate the tool manifest for agent registration.
        
        Returns:
            Dictionary containing tool manifest information
        """
        manifest = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema
        }
        
        return manifest
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate input parameters against the tool schema.
        
        This is a basic implementation. Subclasses can override
        to provide more sophisticated validation.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if parameters are valid, False otherwise
        """
        # Basic validation - subclasses can implement more sophisticated logic
        if not self.input_schema:
            return True  # No schema means accept all parameters
        
        # For now, just check if required fields are present
        required_fields = self.input_schema.get("required", [])
        for field in required_fields:
            if field not in parameters:
                return False
        
        return True
    
    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """
        Get usage examples for the tool.
        
        Subclasses can override this to provide helpful examples
        of how to use the tool.
        
        Returns:
            List of usage examples
        """
        return []
    
    def record_usage(self) -> None:
        """
        Record that the tool was used.
        
        This method can be called by agents to track tool usage
        for monitoring and analytics purposes.
        """
        from datetime import datetime
        
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        
        self.last_used = datetime.now(timezone.utc)
        self.usage_count += 1
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for the tool.
        
        Returns:
            Dictionary containing usage statistics
        """
        stats = {
            "name": self.name,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None
        }
        
        return stats
    
    def __str__(self) -> str:
        """String representation of the tool."""
        return f"{self.name} - {self.description}"
    
    def __repr__(self) -> str:
        """Detailed string representation of the tool."""
        return (f"BaseTool(name='{self.name}', description='{self.description}', "
                f"version='{self.version}', category='{self.category}')")
