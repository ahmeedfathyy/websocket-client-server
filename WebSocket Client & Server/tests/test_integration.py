import pytest
import pytest_asyncio
import asyncio
import websockets
from src.server import handleWebSocketConnection
from src.client import MathClient


@pytest_asyncio.fixture
async def testServer():
    """
    Creates a test WebSocket server instance for integration testing.
    
    The server runs on port 8766 to avoid conflicts with production instances.
    """
    async with websockets.serve(handleWebSocketConnection, "localhost", 8766):
        yield

@pytest.mark.asyncio
async def test_add_numbers_integration(testServer):
    """
    Integration test for the complete client-server workflow.
    
    Tests various scenarios including:
    - Positive integers
    - Floating point numbers
    - Negative numbers
    - Zero values
    - Invalid input handling
    - Large numbers
    """
    mathClient = MathClient(uri="ws://localhost:8766")
    
    # Test positive integers
    calculationResult = await mathClient.callAddNumbers(10, 5)
    assert calculationResult == 15

    # Test floating point numbers
    calculationResult = await mathClient.callAddNumbers(10.5, 0.5)
    assert calculationResult == 11.0

    # Test negative numbers
    calculationResult = await mathClient.callAddNumbers(-5, -5)
    assert calculationResult == -10

    # Test zero values
    calculationResult = await mathClient.callAddNumbers(0, 0)
    assert calculationResult == 0
    await mathClient.close()
    
    # Test invalid input handling - string with number
    mathClient = MathClient(uri="ws://localhost:8766")
    with pytest.raises(Exception) as exceptionInfo:
        await mathClient.callAddNumbers("a", 5)
    assert "error" in str(exceptionInfo.value)
    await mathClient.close()

    # Test large numbers
    mathClient = MathClient(uri="ws://localhost:8766")
    calculationResult = await mathClient.callAddNumbers(1e10, 1e10)
    assert calculationResult == 2e10
    await mathClient.close()

    # Test string inputs
    mathClient = MathClient(uri="ws://localhost:8766")
    with pytest.raises(Exception) as exceptionInfo:
        await mathClient.callAddNumbers("Hey", "Hallo")
    assert "error" in str(exceptionInfo.value)
    await mathClient.close()