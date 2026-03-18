import asyncio
import time

async def mock_analyze_message(content: str):
    # Simulate a network call with 100ms latency
    await asyncio.sleep(0.1)
    return {"sentiment": "neutral", "classification": "discussion", "topics": []}

async def run_sequential(count=20):
    start_time = time.perf_counter()
    results = []
    for i in range(count):
        res = await mock_analyze_message(f"Message {i}")
        results.append(res)
    end_time = time.perf_counter()
    return end_time - start_time

async def run_concurrent(count=20):
    start_time = time.perf_counter()
    tasks = [mock_analyze_message(f"Message {i}") for i in range(count)]
    results = await asyncio.gather(*tasks)
    end_time = time.perf_counter()
    return end_time - start_time

async def main():
    count = 20
    print(f"Benchmarking with {count} messages...")

    seq_time = await run_sequential(count)
    print(f"Sequential time: {seq_time:.4f} seconds")

    con_time = await run_concurrent(count)
    print(f"Concurrent time: {con_time:.4f} seconds")

    improvement = (seq_time - con_time) / seq_time * 100
    print(f"Improvement: {improvement:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
