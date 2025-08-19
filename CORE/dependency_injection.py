"""
Dependency injection container for the Trade Project.

This module provides a simple dependency injection container
that manages component dependencies and their lifecycle.
"""

from typing import Dict, Any, Optional, Type, Callable
from abc import ABC, abstractmethod


class ServiceProvider(ABC):
    """Abstract base class for service providers."""
    
    @abstractmethod
    def get_service(self, service_type: Type) -> Any:
        """Get a service instance of the specified type."""
        pass
    
    @abstractmethod
    def register_service(self, service_type: Type, factory: Callable[[], Any]) -> None:
        """Register a service factory."""
        pass


class DependencyContainer(ServiceProvider):
    """
    Simple dependency injection container.
    
    This class manages the creation and lifecycle of application services,
    ensuring proper dependency resolution and singleton management.
    """
    
    def __init__(self):
        """Initialize the dependency container."""
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
    
    def register_service(self, service_type: Type, factory: Callable[[], Any]) -> None:
        """
        Register a service factory.
        
        Args:
            service_type: The type of service to register
            factory: Factory function that creates the service
        """
        self._factories[service_type] = factory
    
    def register_singleton(self, service_type: Type, instance: Any) -> None:
        """
        Register a singleton service instance.
        
        Args:
            service_type: The type of service to register
            instance: The service instance
        """
        self._singletons[service_type] = instance
    
    def get_service(self, service_type: Type) -> Any:
        """
        Get a service instance of the specified type.
        
        Args:
            service_type: The type of service to retrieve
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service type is not registered
        """
        # Check if it's a singleton
        if service_type in self._singletons:
            return self._singletons[service_type]
        
        # Check if we have a factory
        if service_type in self._factories:
            # Create new instance
            instance = self._factories[service_type]()
            return instance
        
        # Check if we have a concrete instance
        if service_type in self._services:
            return self._services[service_type]
        
        raise KeyError(f"Service type {service_type.__name__} is not registered")
    
    def has_service(self, service_type: Type) -> bool:
        """
        Check if a service type is registered.
        
        Args:
            service_type: The type of service to check
            
        Returns:
            True if service is registered, False otherwise
        """
        return (service_type in self._factories or 
                service_type in self._singletons or 
                service_type in self._services)
    
    def clear(self) -> None:
        """Clear all registered services and factories."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()


# Global dependency container instance
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """Get the global dependency container instance."""
    return _container


def register_service(service_type: Type, factory: Callable[[], Any]) -> None:
    """Register a service factory in the global container."""
    _container.register_service(service_type, factory)


def register_singleton(service_type: Type, instance: Any) -> None:
    """Register a singleton service instance in the global container."""
    _container.register_singleton(service_type, instance)


def get_service(service_type: Type) -> Any:
    """Get a service instance from the global container."""
    return _container.get_service(service_type)


def has_service(service_type: Type) -> bool:
    """Check if a service type is registered in the global container."""
    return _container.has_service(service_type)
