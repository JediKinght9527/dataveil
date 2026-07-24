"""Performance benchmark script for DataVeil Gateway."""
import asyncio
import statistics
import time

import httpx


async def benchmark_gateway(
    url: str = "http://127.0.0.1:8787/v1/messages",
    requests: int = 100,
    concurrency: int = 10,
) -> dict:
    """Run a simple benchmark against the gateway."""

    payload = {
        "model": "kimi-k2.6",
        "messages": [{"role": "user", "content": "Hello, my email is test@example.com"}],
        "max_tokens": 10,
    }

    latencies: list[float] = []
    errors = 0

    async def make_request(client: httpx.AsyncClient):
        nonlocal errors
        start = time.perf_counter()
        try:
            resp = await client.post(url, json=payload, timeout=30.0)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            return resp.status_code
        except Exception:
            errors += 1
            return 0

    async with httpx.AsyncClient() as client:
        # Warmup
        await make_request(client)

        # Benchmark
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_request():
            async with semaphore:
                return await make_request(client)

        tasks = [bounded_request() for _ in range(requests)]
        await asyncio.gather(*tasks)

    if not latencies:
        return {"error": "all requests failed"}

    return {
        "total_requests": requests,
        "concurrency": concurrency,
        "errors": errors,
        "avg_ms": round(statistics.mean(latencies), 2),
        "p50_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(statistics.quantiles(latencies, n=20)[18], 2) if len(latencies) >= 20 else None,
        "p99_ms": round(statistics.quantiles(latencies, n=100)[98], 2) if len(latencies) >= 100 else None,
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
    }


if __name__ == "__main__":
    result = asyncio.run(benchmark_gateway())
    print("Benchmark Results:")
    for k, v in result.items():
        print(f"  {k}: {v}")
