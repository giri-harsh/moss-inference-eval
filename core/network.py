"""Round-trip floor to both providers: 15 free GET /models calls each over a reused connection."""

import asyncio
import time

import common


async def main():
    log = common.Log("network")
    async with common.http_client() as client:
        for i in range(15):
            for provider in ("moss", "groq"):
                start = time.perf_counter()
                r = await client.get(common.PROVIDERS[provider]["base"] + "/models",
                                     headers={"Authorization": common.auth_header(provider)})
                log.write({"provider": provider, "i": i, "status": r.status_code,
                           "ms": round((time.perf_counter() - start) * 1000, 1)})
            await asyncio.sleep(0.6)


asyncio.run(main())
