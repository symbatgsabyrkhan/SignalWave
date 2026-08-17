"""SignalWave local concurrency load test.

Measures response latency for 20 concurrent analysis requests
against the running FastAPI web server.

Target from assignment:
p95 analysis latency < 5 seconds under 20 concurrent users.
"""

from __future__ import annotations

import asyncio
import statistics
import time

import httpx

BASE_URL = "http://127.0.0.1:8000"

CONCURRENCY = 20

SYMBOL = "BTCUSDT"
TIMEFRAME = "1d"


async def one_request(
    client: httpx.AsyncClient,
    request_id: int,
) -> tuple[int, float, int]:
    url = (
        f"{BASE_URL}/api/binance"
        f"?symbol={SYMBOL}"
        f"&timeframe={TIMEFRAME}"
    )

    started = time.perf_counter()

    try:
        response = await client.get(url)

        elapsed = (
            time.perf_counter()
            - started
        )

        return (
            request_id,
            elapsed,
            response.status_code,
        )

    except Exception:
        elapsed = (
            time.perf_counter()
            - started
        )

        return (
            request_id,
            elapsed,
            0,
        )


def percentile(
    values: list[float],
    percentile_value: float,
) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)

    index = (
        len(ordered) - 1
    ) * percentile_value

    lower = int(index)
    upper = min(
        lower + 1,
        len(ordered) - 1,
    )

    fraction = (
        index - lower
    )

    return (
        ordered[lower]
        + (
            ordered[upper]
            - ordered[lower]
        )
        * fraction
    )


async def main() -> None:
    print()
    print("=" * 72)
    print(
        "SIGNALWAVE LOAD TEST"
    )
    print("=" * 72)

    print(
        f"Target: {BASE_URL}"
    )

    print(
        f"Concurrent requests: {CONCURRENCY}"
    )

    print(
        f"Market: {SYMBOL} {TIMEFRAME}"
    )

    print()

    timeout = httpx.Timeout(
        60.0
    )

    limits = httpx.Limits(
        max_connections=CONCURRENCY,
        max_keepalive_connections=CONCURRENCY,
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
    ) as client:

        started_all = (
            time.perf_counter()
        )

        tasks = [
            one_request(
                client,
                request_id,
            )
            for request_id
            in range(
                1,
                CONCURRENCY + 1,
            )
        ]

        results = await asyncio.gather(
            *tasks
        )

        total_elapsed = (
            time.perf_counter()
            - started_all
        )

    latencies = [
        elapsed
        for _,
        elapsed,
        status
        in results
        if status == 200
    ]

    failed = [
        result
        for result in results
        if result[2] != 200
    ]

    print(
        "RESULTS"
    )

    print(
        "-" * 72
    )

    for (
        request_id,
        elapsed,
        status,
    ) in results:

        print(
            f"#{request_id:02d} "
            f"status={status:<3} "
            f"latency={elapsed:.3f}s"
        )

    print()
    print(
        "=" * 72
    )
    print(
        "SUMMARY"
    )
    print(
        "=" * 72
    )

    print(
        f"Successful: "
        f"{len(latencies)}/"
        f"{CONCURRENCY}"
    )

    print(
        f"Failed: "
        f"{len(failed)}"
    )

    print(
        f"Total wall time: "
        f"{total_elapsed:.3f}s"
    )

    if latencies:
        mean_latency = (
            statistics.mean(
                latencies
            )
        )

        median_latency = (
            statistics.median(
                latencies
            )
        )

        p95 = percentile(
            latencies,
            0.95,
        )

        maximum = max(
            latencies
        )

        print(
            f"Mean latency: "
            f"{mean_latency:.3f}s"
        )

        print(
            f"Median latency: "
            f"{median_latency:.3f}s"
        )

        print(
            f"p95 latency: "
            f"{p95:.3f}s"
        )

        print(
            f"Max latency: "
            f"{maximum:.3f}s"
        )

        print()

        if (
            len(latencies)
            == CONCURRENCY
            and p95 < 5.0
        ):
            print(
                "PASS: p95 < 5s "
                "under 20 concurrent analyses."
            )
        else:
            print(
                "FAIL: assignment latency "
                "target not met."
            )

    else:
        print(
            "No successful responses."
        )

    if failed:
        print()
        print(
            "Failed request details:"
        )

        for (
            request_id,
            elapsed,
            status,
        ) in failed:
            print(
                f"#{request_id}: "
                f"status={status}, "
                f"{elapsed:.3f}s"
            )


if __name__ == "__main__":
    asyncio.run(main())