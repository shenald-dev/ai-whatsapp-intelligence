import asyncio
import threading

async def my_coro():
    return 42

def worker():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        res = loop.run_until_complete(my_coro())
        print(f"Worker success: {res}")
    except Exception as e:
        print(f"Worker error: {type(e).__name__} - {e}")

t = threading.Thread(target=worker)
t.start()
t.join()
