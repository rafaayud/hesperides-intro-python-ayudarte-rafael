"""
Custom metaclasses for the trading domain.
"""
import logging
import inspect
from abc import ABCMeta, ABC
from typing import Type, Dict, Any

logger = logging.getLogger(__name__)


class AdapterMeta(ABCMeta):
    """
    Metaclass that checks that an adapter implements all the methods defined in its port (interface).
    
    Detects errors at class definition time, not at runtime.
    Automatically detects the port from the base classes (no need for _implements).
    
    Usage:
        class StoragePort(ABC):
            @abstractmethod
            async def save_candle(self, candle): ...
            
            @abstractmethod
            async def get_candles(self, symbol, interval): ...
        
        class PostgreAdapter(StoragePort, metaclass=AdapterMeta):
            async def save_candle(self, candle):
                ...
            
            # Error: Missing get_candles
            # TypeError: PostgreAdapter does not implement: get_candles
    """
    
    def __new__(mcs, name: str, bases: tuple, namespace: Dict[str, Any]) -> Type:
        cls = super().__new__(mcs, name, bases, namespace)
        
        # Auto-detect port from base classes (find ABC subclass that ends with "Port")
        port = None
        for base in bases:
            if base.__name__.endswith('Port') and issubclass(base, ABC):
                port = base
                break
        
        if port is None:
            return cls
        
        # Get the abstract methods of the port
        port_methods = set()
        for method_name in dir(port):
            if method_name.startswith('_'):
                continue
            method = getattr(port, method_name)
            if callable(method) and getattr(method, '__isabstractmethod__', False):
                port_methods.add(method_name)
        
        # Check that all are implemented
        missing = []
        wrong_signature = []
        
        for method_name in port_methods:
            if not hasattr(cls, method_name):
                missing.append(method_name)
                continue
            
            adapter_method = getattr(cls, method_name)
            
            # Check that it is not still abstract
            if getattr(adapter_method, '__isabstractmethod__', False):
                missing.append(method_name)
                continue
            
            # Check the signature (parameters)
            port_method = getattr(port, method_name)
            port_sig = inspect.signature(port_method)
            adapter_sig = inspect.signature(adapter_method)
            
            port_params = list(port_sig.parameters.keys())
            adapter_params = list(adapter_sig.parameters.keys())
            
            if port_params != adapter_params:
                wrong_signature.append(
                    f"{method_name}: esperado {port_params}, tiene {adapter_params}"
                )
        
        # Report errors
        errors = []
        
        if missing:
            errors.append(f"Methods not implemented: {missing}")
        
        if wrong_signature:
            errors.append(f"Incorrect signatures: {wrong_signature}")
        
        if errors:
            raise TypeError(
                f"Adapter '{name}' does not comply with '{port.__name__}':\n  " + 
                "\n  ".join(errors)
            )
        
        logger.debug(f"{name} implements {port.__name__} correctly")
        return cls

