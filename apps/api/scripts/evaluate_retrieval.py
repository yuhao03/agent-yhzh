import asyncio
import json
from pathlib import Path

from agent_yhzh.config import settings
from agent_yhzh.database import session_factory
from agent_yhzh.services.retrieval import hybrid_search


async def main() -> None:
    cases = json.loads(
        (Path(__file__).parents[1] / "evals" / "golden.json").read_text("utf-8")
    )
    passed = 0
    async with session_factory() as session:
        for case in cases:
            results = await hybrid_search(
                session,
                case["query"],
                tenant_id=settings.default_tenant_id,
                space_id=settings.default_space_id,
                limit=5,
            )
            titles = [result.item.title for result in results]
            ok = any(case["expected_title_contains"] in title for title in titles)
            passed += int(ok)
            print(json.dumps({"query": case["query"], "passed": ok, "titles": titles}, ensure_ascii=False))
    print(f"retrieval_eval={passed}/{len(cases)}")


if __name__ == "__main__":
    asyncio.run(main())
