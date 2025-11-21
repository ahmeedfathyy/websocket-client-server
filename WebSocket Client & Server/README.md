# WebSocket Client & Server Exercise

This package implements a WebSocket server that performs calculations and a client that requests them.

Environment Setup

1. **Prerequisites:** Python 3.10+
2. **Create Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

websockets>=12.0
#This is the main library used to create the server and client connections.
pytest>=8.0
#This is the testing framework needed to run the automated tests mentioned in the "Optional / Bonus Tasks"
pytest-asyncio>=0.23
#Since the functions must be async, this specific plugin allows pytest to test asynchronous code correctly.

## Example Output
2025-11-21 15:23:47,983 - CLIENT - INFO - Sending request: {'action': 'add', 'params': {'a': -100, 'b': 100}}
Result of -100 + 100 = 0
...