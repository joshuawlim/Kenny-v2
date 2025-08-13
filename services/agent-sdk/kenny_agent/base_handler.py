"""
Base Capability Handler for the Kenny v2 multi-agent system.

This class provides the foundation for implementing agent capabilities,
including execution logic and manifest generation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseCapabilityHandler(ABC):
    """
    Base class for implementing agent capabilities.
    
    Capability handlers implement specific functionality that agents can
    provide, such as searching, reading, or processing data.
    """
    
    def __init__(
        self,
        capability: str,
        description: str,
        version: str = "1.0.0",
        parameters_schema: Optional[Dict[str, Any]] = None,
        returns_schema: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the capability handler.
        
        Args:
            capability: Full capability name (e.g., 'messages.search')
            description: Human-readable description of the capability
            version: Version string for the capability
            parameters_schema: JSON Schema for input parameters
            returns_schema: JSON Schema for return values
        """
        self.capability = capability
        self.description = description
        self.version = version
        self.parameters_schema = parameters_schema or {}
        self.returns_schema = returns_schema or {}
        
        # Parse capability into verb and noun
        if '.' in capability:
            self.verb, self.noun = capability.split('.', 1)
        else:
            self.verb = capability
            self.noun = ""
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the capability with the given parameters.
        
        This method must be implemented by subclasses to provide
        the actual capability functionality.
        
        Args:
            parameters: Input parameters for the capability
            
        Returns:
            Result of the capability execution
            
        Raises:
            Exception: If the capability execution fails
        """
        raise NotImplementedError("Subclasses must implement execute method")
    
    def get_manifest(self) -> Dict[str, Any]:
        """
        Generate the capability manifest for agent registration.
        
        Returns:
            Dictionary containing capability manifest information
        """
        manifest = {
            "capability": self.capability,
            "verb": self.verb,
            "noun": self.noun,
            "description": self.description,
            "version": self.version,
            "parameters_schema": self.parameters_schema,
            "returns_schema": self.returns_schema
        }
        
        return manifest
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate input parameters against the capability schema.
        
        This is a basic implementation. Subclasses can override
        to provide more sophisticated validation.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if parameters are valid, False otherwise
        """
        # Basic validation - subclasses can implement more sophisticated logic
        if not self.parameters_schema:
            return True  # No schema means accept all parameters
        
        # For now, just check if required fields are present
        required_fields = self.parameters_schema.get("required", [])
        for field in required_fields:
            if field not in parameters:
                return False
        
        return True
    
    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """
        Get usage examples for the capability.
        
        Subclasses can override this to provide helpful examples
        of how to use the capability.
        
        Returns:
            List of usage examples
        """
        return []
    
    def __str__(self) -> str:
        """String representation of the capability handler."""
        return f"{self.capability} - {self.description}"
    
    def __repr__(self) -> str:
        """Detailed string representation of the capability handler."""
        return (f"BaseCapabilityHandler(capability='{self.capability}', "
                f"description='{self.description}', version='{self.version}')")
