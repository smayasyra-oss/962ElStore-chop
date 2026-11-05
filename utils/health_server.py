"""خادم صحة صغير جداً: يسمح باستخدام Render Web Service (المجاني) دون موقع حقيقي."""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_RESPONSE = (
    b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n"
    b"Content-Length: 2\r\nConnection: close\r\n\r\nok"
)


async def start_health_server(port: int) -> asyncio.AbstractServer:
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            await asyncio.wait_for(reader.read(1024), timeout=5)
            writer.write(_RESPONSE)
            await writer.drain()
        except Exception:  # noqa: BLE001
            pass
        finally:
            writer.close()

    server = await asyncio.start_server(handle, "0.0.0.0", port)
    logger.info("خادم الصحة يعمل على المنفذ %s", port)
    return server
