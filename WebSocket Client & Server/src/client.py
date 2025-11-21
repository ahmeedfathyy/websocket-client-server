import asyncio
import websockets
import json
import logging
from typing import Optional, Dict, Any

# Configure logging for the client
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - CLIENT - %(levelname)s - %(message)s"
)

# Custom exception classes for better error handling
class MathClientError(Exception):
    """Base exception for MathClient errors"""
    pass

class ConnectionError(MathClientError):
    """Raised when connection to server fails"""
    pass

class ServerError(MathClientError):
    """Raised when server returns an error"""
    pass

# Main WebSocket client class for mathematical operations
class MathClient:
    """
    WebSocket client for performing mathematical operations with a remote server.
    
    Attributes:
        serverUri: The WebSocket server URI to connect to
        connectionTimeout: Maximum time to wait for operations in seconds
        maximumRetryAttempts: Number of retry attempts for failed operations
    """
    
    def __init__(self, uri: str = "ws://localhost:8765", timeout: float = 10.0, maxRetries: int = 3):
        self.serverUri = uri
        self.connectionTimeout = timeout
        self.maximumRetryAttempts = maxRetries
        self._websocketConnection: Any = None 

    async def connect(self):
        """
        Establishes a connection to the WebSocket server.
        
        Raises:
            ConnectionError: If the connection attempt fails
        """
        logging.info(f"Connecting to {self.serverUri}...")
        try:
            self._websocketConnection = await websockets.connect(self.serverUri, open_timeout=self.connectionTimeout)
            logging.info("Connected successfully.")
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}")

    async def close(self):
        """
        Closes the WebSocket connection gracefully.
        """
        if self._websocketConnection:
            logging.info("Closing connection...")
            await self._websocketConnection.close()
            self._websocketConnection = None
            logging.info("Connection closed.")

    # Context manager support for automatic connection management
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensureConnectionIsActive(self):
        """
        Verifies the WebSocket connection is active and reconnects if necessary.
        
        Checks the close_code attribute to determine connection state:
        - None indicates an open connection
        - Integer value indicates a closed connection
        """
        if self._websocketConnection is None or self._websocketConnection.close_code is not None:
            logging.warning("Connection lost or not open. Reconnecting...")
            await self.connect()

    async def callAddNumbers(self, firstOperand: float, secondOperand: float) -> float:
        """
        Sends a request to the server to add two numbers.
        
        Implements automatic retry logic for network-related failures.
        
        Args:
            firstOperand: The first number to add
            secondOperand: The second number to add
        
        Returns:
            The sum of the two operands
        
        Raises:
            ValueError: If parameters are not numeric
            ServerError: If the server returns an error response
            ConnectionError: If connection fails after all retry attempts
        """
        # Validate input types
        if not isinstance(firstOperand, (int, float)) or not isinstance(secondOperand, (int, float)):
            raise ValueError(f"Parameters must be numeric, got a={type(firstOperand)}, b={type(secondOperand)}")
        
        requestPayload = {
            "action": "add",
            "params": {"a": firstOperand, "b": secondOperand}
        }

        lastException = None
        
        # Retry loop for handling transient network failures
        for attemptNumber in range(self.maximumRetryAttempts):
            try:
                await self._ensureConnectionIsActive()
                
                if not self._websocketConnection:
                    raise ConnectionError("Failed to obtain websocket connection")

                async with asyncio.timeout(self.connectionTimeout):
                    logging.debug(f"Sending: {requestPayload}")
                    await self._websocketConnection.send(json.dumps(requestPayload))
                    
                    rawResponseData = await self._websocketConnection.recv()
                    
                    # Parse the JSON response
                    try:
                        parsedResponse: Dict[str, Any] = json.loads(rawResponseData)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Server returned invalid JSON: {e}")

                    # Validate response structure
                    if "status" not in parsedResponse:
                        raise ValueError("Server response missing 'status' field")

                    if parsedResponse.get("status") == "success":
                        if "result" not in parsedResponse:
                            raise ValueError("Server response missing 'result' field")
                        
                        operationResult = parsedResponse["result"]
                        if not isinstance(operationResult, (int, float)):
                            raise ValueError(f"Expected numeric result, got {type(operationResult)}")
                        
                        return operationResult
                    else:
                        # Server returned an error (not retryable)
                        errorMessage = parsedResponse.get("message", "Unknown error")
                        raise ServerError(errorMessage)

            except (OSError, websockets.exceptions.WebSocketException, asyncio.TimeoutError, ConnectionError) as e:
                # Network errors are retryable
                lastException = ConnectionError(f"Network error: {e}")
                logging.warning(f"Attempt {attemptNumber + 1} failed: {e}")
                
                # Clear the connection to force reconnection
                self._websocketConnection = None
                
                if attemptNumber < self.maximumRetryAttempts - 1:
                    await asyncio.sleep(2 ** attemptNumber)
                    
            except (ServerError, ValueError) as e:
                logging.error(f"Non-retryable error: {e}")
                raise
                
            except Exception as e:
                logging.error(f"Unexpected error: {e}", exc_info=True)
                raise MathClientError(f"Unexpected error: {e}")

        raise lastException if lastException else ConnectionError("Connection failed after retries")

# Interactive session functionality
async def getUserInputAsync(promptMessage: str) -> str:
    """
    Retrieves user input asynchronously without blocking the event loop.
    
    This allows the WebSocket connection to remain active (ping/pong) 
    while waiting for user input.
    
    Args:
        promptMessage: The prompt text to display to the user
    
    Returns:
        The user's input as a string
    """
    return await asyncio.get_running_loop().run_in_executor(None, input, promptMessage)

async def runInteractiveSession():
    """
    Runs an interactive command-line session for the math client.
    
    Allows users to repeatedly send addition requests to the server
    until they choose to exit.
    """
    mathClient = MathClient(timeout=5.0, maxRetries=3)

    print("--- Connecting to Server ---")
    
    try:
        # Establish connection once and reuse it
        async with mathClient:
            print("Connected! (Type 'exit' or 'q' to quit)")
            print("-----------------------------------")

            # Process user requests in a loop
            while True:
                try:
                    # Get user input without blocking the connection
                    userInput = await getUserInputAsync("\nEnter two numbers (e.g., '10 20'): ")
                    
                    if userInput.lower() in ['exit', 'quit', 'q']:
                        print("Exiting...")
                        break
                    
                    inputParts = userInput.split()
                    if len(inputParts) != 2:
                        print("Please enter exactly two numbers separated by a space.")
                        continue
                        
                    firstNumber = float(inputParts[0])
                    secondNumber = float(inputParts[1])

                    # Send request using the existing connection
                    calculationResult = await mathClient.callAddNumbers(firstNumber, secondNumber)
                    print(f"Result: {calculationResult}")

                except ValueError:
                    print("Invalid input. Please enter numbers only.")
                except ServerError as e:
                    print(f"Server Error: {e}")
                except ConnectionError as e:
                    print(f"Connection Error: {e}")
                    # Connection will be re-established on next attempt

    except Exception as e:
        print(f"Fatal Error: {e}")

    print("--- Connection Closed ---")

if __name__ == "__main__":
    try:
        asyncio.run(runInteractiveSession())
    except KeyboardInterrupt:
        pass