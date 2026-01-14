"""
Test for AdapterMeta metaclass.
Verifies that adapters must implement all port methods.
"""
import pytest
from abc import ABC, abstractmethod
from src.trading.domain.utils import AdapterMeta


class TestPort(ABC):
    """Test port with abstract methods"""
    
    @abstractmethod
    async def connect(self) -> None:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass
    
    @abstractmethod
    async def do_something(self, param: str) -> str:
        pass


def test_adapter_meta_valid_adapter() -> None:
    """Test that a valid adapter passes validation"""
    
    # This should NOT raise an error
    class ValidAdapter(TestPort, metaclass=AdapterMeta):
        async def connect(self) -> None:
            pass
        
        async def disconnect(self) -> None:
            pass
        
        async def do_something(self, param: str) -> str:
            return param
    
    adapter = ValidAdapter()
    assert adapter is not None
    print("✓ Valid adapter created successfully")


def test_adapter_meta_missing_method() -> None:
    """Test that missing methods raise TypeError"""
    
    with pytest.raises(TypeError) as exc_info:
        # This SHOULD raise TypeError because do_something is missing
        class InvalidAdapter(TestPort, metaclass=AdapterMeta):
            async def connect(self) -> None:
                pass
            
            async def disconnect(self) -> None:
                pass
            
            # Missing: do_something
    
    error_message = str(exc_info.value)
    assert "InvalidAdapter" in error_message
    assert "do_something" in error_message
    print(f"✓ Correctly raised error: {error_message}")


def test_adapter_meta_wrong_signature() -> None:
    """Test that wrong method signatures raise TypeError"""
    
    with pytest.raises(TypeError) as exc_info:
        # This SHOULD raise TypeError because signature is wrong
        class WrongSignatureAdapter(TestPort, metaclass=AdapterMeta):
            async def connect(self) -> None:
                pass
            
            async def disconnect(self) -> None:
                pass
            
            # Wrong signature: missing 'param'
            async def do_something(self) -> str:
                return "wrong"
    
    error_message = str(exc_info.value)
    assert "WrongSignatureAdapter" in error_message
    assert "do_something" in error_message
    print(f"✓ Correctly raised error: {error_message}")


def test_real_adapters_are_valid() -> None:
    """Test that our real adapters pass validation"""
    
    # These imports will fail if adapters don't implement all methods
    from src.trading.infrastructure.postgre_adapter import PostgreAdapter
    from src.trading.infrastructure.binance_adapter import BinanceAdapter
    from src.trading.infrastructure.binance_stream_adapter import BinanceStreamAdapter
    from src.trading.infrastructure.mocks.mock_exchange_adapter import MockExchangeAdapter
    from src.trading.infrastructure.mocks.mock_stream_adapter import MockStreamAdapter
    from src.trading.infrastructure.mocks.mock_storage_adapter import MockStorageAdapter
    
    print("✓ All real adapters implement their ports correctly")


if __name__ == "__main__":
    print("\n=== Testing AdapterMeta ===\n")
    
    test_adapter_meta_valid_adapter()
    test_adapter_meta_missing_method()
    test_adapter_meta_wrong_signature()
    test_real_adapters_are_valid()
    
    print("\n=== All tests passed! ===\n")

