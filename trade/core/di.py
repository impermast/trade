"""
Dependency Injection system for the Trade Project.

This module provides a simple dependency injection container that can be used
to manage dependencies between components.
"""

from typing import Dict, Any, Callable, TypeVar, Type, Optional, cast

T = TypeVar('T')


class DIContainer:
    """
    A simple dependency injection container.
    
    This container manages dependencies between components by storing
    factory functions that create instances of components.
    """
    
    def __init__(self) -> None:
        """Initialize an empty container."""
        self._factories: Dict[str, Callable[..., Any]] = {}
        self._instances: Dict[str, Any] = {}
    
    def register(self, name: str, factory: Callable[..., T]) -> None:
        """
        Register a factory function for a component.
        
        Args:
            name: Name of the component
            factory: Factory function that creates an instance of the component
        """
        self._factories[name] = factory
    
    def register_instance(self, name: str, instance: T) -> None:
        """
        Register an existing instance of a component.
        
        Args:
            name: Name of the component
            instance: Instance of the component
        """
        self._instances[name] = instance
    
    def get(self, name: str, **kwargs: Any) -> Any:
        """
        Get an instance of a component.
        
        If the component has already been instantiated, the existing instance
        is returned. Otherwise, the factory function is called to create a new
        instance.
        
        Args:
            name: Name of the component
            **kwargs: Additional arguments to pass to the factory function
        
        Returns:
            An instance of the component
        
        Raises:
            KeyError: If the component is not registered
        """
        # Return existing instance if available
        if name in self._instances:
            return self._instances[name]
        
        # Create new instance using factory
        if name in self._factories:
            instance = self._factories[name](**kwargs)
            self._instances[name] = instance
            return instance
        
        raise KeyError(f"Component '{name}' not registered")
    
    def get_factory(self, name: str) -> Callable[..., Any]:
        """
        Get the factory function for a component.
        
        Args:
            name: Name of the component
        
        Returns:
            The factory function for the component
        
        Raises:
            KeyError: If the component is not registered
        """
        if name in self._factories:
            return self._factories[name]
        
        raise KeyError(f"Component '{name}' not registered")
    
    def clear(self) -> None:
        """Clear all registered components and instances."""
        self._factories.clear()
        self._instances.clear()


# Global container instance
container = DIContainer()


def register(name: str, factory: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to register a factory function with the global container.
    
    Args:
        name: Name of the component
        factory: Factory function that creates an instance of the component
    
    Returns:
        The factory function (unchanged)
    """
    container.register(name, factory)
    return factory


def get(name: str, **kwargs: Any) -> Any:
    """
    Get an instance of a component from the global container.
    
    Args:
        name: Name of the component
        **kwargs: Additional arguments to pass to the factory function
    
    Returns:
        An instance of the component
    """
    return container.get(name, **kwargs)