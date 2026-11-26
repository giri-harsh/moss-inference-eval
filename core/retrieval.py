"""MossClient.query access. It downloads the index and embeds the query in-process, so scores come from here."""

import time

from moss import MossClient, QueryOptions

import common


async def load(index=common.INDEX):
    common.require("MOSS_PROJECT_ID", "MOSS_PROJECT_KEY")
    client = MossClient(common.SECRETS["MOSS_PROJECT_ID"], common.SECRETS["MOSS_PROJECT_KEY"])
    await client.load_index(index)
    await client.query(index, "warm up", QueryOptions(top_k=1))
    return client


async def search(client, text, phase, top_k=5, index=common.INDEX):
    common.guard(0.001, phase)
    start = time.perf_counter()
    result = await client.query(index, text, QueryOptions(top_k=top_k))
    wall = round((time.perf_counter() - start) * 1000, 2)
    common.charge("local_query", 0.0005, phase)  # counted at the published text-query price, to stay conservative
    chunks = [{"id": d.id, "score": round(d.score, 4)} for d in result.docs]
    return {"query": text, "chunks": chunks, "wall_ms": wall, "engine_ms": result.time_taken_ms}
