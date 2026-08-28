import json
import logging
from typing import List, Set
from fastapi import WebSocket

logger = logging.getLogger("ws_manager")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message_type: str, payload: dict):
        """Broadcasts event payload to all active browser UI clients."""
        if not self.active_connections:
            return

        data = json.dumps({"type": message_type, "data": payload})
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.active_connections.discard(dead)

ws_manager = ConnectionManager()
