"""Create or delete the Moss index of one KB level: `python -m core.build_index 0`, `... 2`, `... 2 --delete`.

One chunk per curated entry or scraped passage, source details kept as metadata. Only the temporary
`akgec-scale-*` indexes can be deleted here (the free plan allows three indexes per account).
"""

import asyncio
import sys
import time

from moss import DocumentInfo, MossClient

import common
from core.corpus import index_name, level


async def main(n, delete):
    common.require("MOSS_PROJECT_ID", "MOSS_PROJECT_KEY")
    name, before = index_name(n), common.spent()
    log = common.Log(f"index_L{n}{'_delete' if delete else ''}")
    client = MossClient(common.SECRETS["MOSS_PROJECT_ID"], common.SECRETS["MOSS_PROJECT_KEY"])
    existing = {i.name: i.doc_count for i in await client.list_indexes()}
    log.write({"existing_indexes": existing})
    if delete:
        assert name.startswith("akgec-scale-"), "refusing to delete a non-temporary index"
        if name in existing:
            log.write({"deleted": name, "result": bool(await client.delete_index(name))})
        print("deleted", name)
        return
    chunks = level(n)[1]
    megabytes = sum(len(text.encode()) for _, text, _ in chunks) / 1e6
    if name not in existing:
        common.guard(megabytes * 0.03 + 0.01, "core")
        start = time.perf_counter()
        result = await client.create_index(name, [DocumentInfo(i, text, meta) for i, text, meta in chunks])
        common.charge("create_index", megabytes * 0.03, "core")  # published ingest price per MB
        log.write({"created": name, "job_id": result.job_id, "documents": len(chunks), "mb": round(megabytes, 3),
                   "build_s": round(time.perf_counter() - start, 1)})
    info = await client.get_index(name)
    log.write({"index": name, "status": str(info.status), "doc_count": info.doc_count, "model": str(info.model.id)})
    print(name, info.status, info.doc_count, f"{megabytes:.2f} MB")
    assert info.doc_count == len(chunks), "index does not hold the expected documents"
    common.report_spend(f"build_index_L{n}", before)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]), "--delete" in sys.argv))
