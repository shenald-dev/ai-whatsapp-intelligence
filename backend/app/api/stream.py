import asyncio
import json
import logging
from typing import Set, AsyncGenerator, Dict, Any

logger = logging.getLogger(__name__)

class EventBus:
    """In-memory asynchronous event broadcaster for real-time Server-Sent Events (SSE)."""

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        logger.debug(f"New SSE client subscribed. Total subscribers: {len(self._subscribers)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)
        logger.debug(f"SSE client unsubscribed. Remaining: {len(self._subscribers)}")

    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publishes an event to all active listeners."""
        if not self._subscribers:
            return

        payload = {
            "event": event_type,
            "data": data
        }
        for q in list(self._subscribers):
            try:
                # If queue is full, drop oldest item to avoid backpressure memory leaks
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(payload)
            except Exception as e:
                logger.debug(f"Error publishing to subscriber queue: {e}")

    async def event_generator(self, queue: asyncio.Queue) -> AsyncGenerator[str, None]:
        """Yields SSE formatted text chunks to an HTTP connection."""
        try:
            # Send initial connection confirmation event
            init_data = json.dumps({"status": "connected", "service": "awi_intelligence_stream"})
            yield f"event: connected\ndata: {init_data}\n\n"

            while True:
                try:
                    # Wait for next event or timeout to send a keep-alive ping
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_type = payload.get("event", "message")
                    data_str = json.dumps(payload.get("data", {}))
                    yield f"event: {event_type}\ndata: {data_str}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat ping comment
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            self.unsubscribe(queue)

event_bus = EventBus()
