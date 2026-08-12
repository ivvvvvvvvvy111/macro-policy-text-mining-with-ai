#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROJECT_ROOT, Settings
from src.io_utils import (
    append_jsonl,
    load_done_ids,
    read_jsonl,
    read_news,
    write_csv,
    write_json,
)
from src.llm_client import StructuredLLM
from src.measure_extract import MeasureExtractor
from src.routing import MeasureRouter
from src.scoring import (
    RelationScorer,
    flatten_all_a_rows,
    flatten_industry_rows,
    flatten_style_rows,
)


write_lock = threading.Lock()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="政策 measure → 路由 → 三轨关系级打分")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "sample_5000.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--stages",
        default="measure,routing,scoring",
        help="comma list: measure,routing,scoring",
    )
    return parser.parse_args()


def _safe_append(path: Path, record: dict[str, Any]) -> None:
    with write_lock:
        append_jsonl(path, record)


def process_one(
    news: dict[str, str],
    *,
    extractor: MeasureExtractor,
    router: MeasureRouter,
    scorer: RelationScorer,
    stages: set[str],
    paths: dict[str, Path],
) -> dict[str, Any]:
    stats = {"measures": 0, "routes": 0, "score_calls": 0, "relations": 0}

    if "measure" not in stages:
        raise RuntimeError("当前实现要求至少包含 measure 阶段")

    extraction = extractor.extract(news)
    pending_routes: list[dict[str, Any]] = []
    pending_scores: list[tuple[Path, dict[str, Any]]] = []
    pending_relations: list[dict[str, Any]] = []

    if extraction.is_policy_news:
        for measure in extraction.measures:
            stats["measures"] += 1
            route = None
            if "routing" in stages:
                route = router.route(title=news["title"], measure=measure)
                pending_routes.append(
                    {
                        "news_id": news["news_id"],
                        "title": news["title"],
                        "measure": measure.model_dump(),
                        "routing": route.model_dump(),
                    }
                )
                stats["routes"] += 1

            if "scoring" not in stages or route is None:
                continue

            measure_dump = measure.model_dump()
            route_dump = route.model_dump()

            if route.industry:
                ind = scorer.score_industry(
                    title=news["title"], measure=measure, routing=route
                )
                pending_scores.append(
                    (
                        paths["scores_industry"],
                        {
                            "news_id": news["news_id"],
                            "measure_id": measure.measure_id,
                            "result": ind.model_dump(),
                        },
                    )
                )
                stats["score_calls"] += 1
                for row in flatten_industry_rows(
                    news=news, measure=measure_dump, routing=route_dump, result=ind
                ):
                    pending_relations.append(row)
                    stats["relations"] += 1

            if route.all_a:
                alla = scorer.score_all_a(title=news["title"], measure=measure)
                pending_scores.append(
                    (
                        paths["scores_all_a"],
                        {
                            "news_id": news["news_id"],
                            "measure_id": measure.measure_id,
                            "result": alla.model_dump(),
                        },
                    )
                )
                stats["score_calls"] += 1
                for row in flatten_all_a_rows(
                    news=news, measure=measure_dump, routing=route_dump, result=alla
                ):
                    pending_relations.append(row)
                    stats["relations"] += 1

            if route.style:
                sty = scorer.score_style(title=news["title"], measure=measure)
                pending_scores.append(
                    (
                        paths["scores_style"],
                        {
                            "news_id": news["news_id"],
                            "measure_id": measure.measure_id,
                            "result": sty.model_dump(),
                        },
                    )
                )
                stats["score_calls"] += 1
                for row in flatten_style_rows(
                    news=news, measure=measure_dump, routing=route_dump, result=sty
                ):
                    pending_relations.append(row)
                    stats["relations"] += 1

    # Commit only after full success so resume does not skip incomplete news.
    _safe_append(paths["measures"], {"news": news, "result": extraction.model_dump()})
    for item in pending_routes:
        _safe_append(paths["routing"], item)
    for path, payload in pending_scores:
        _safe_append(path, payload)
    for row in pending_relations:
        _safe_append(paths["scores_relations_jsonl"], row)

    return stats


def rebuild_csv(output_dir: Path) -> int:
    rows = read_jsonl(output_dir / "scores_relations.jsonl")
    write_csv(output_dir / "scores_relations.csv", rows)
    return len(rows)


def main() -> int:
    args = parse_args()
    resume = args.resume and not args.no_resume and not args.overwrite
    stages = {s.strip() for s in args.stages.split(",") if s.strip()}
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "measures": output_dir / "measures.jsonl",
        "routing": output_dir / "routing_results.jsonl",
        "scores_industry": output_dir / "scores_industry.jsonl",
        "scores_all_a": output_dir / "scores_all_a.jsonl",
        "scores_style": output_dir / "scores_style.jsonl",
        "scores_relations_jsonl": output_dir / "scores_relations.jsonl",
        "errors": output_dir / "errors.jsonl",
    }

    news_rows = read_news(args.input.resolve(), args.limit)
    if not news_rows:
        raise RuntimeError("输入没有可处理新闻")

    prompts = {
        "measure": PROJECT_ROOT / "prompts" / "measure_prompt.txt",
        "routing": PROJECT_ROOT / "prompts" / "routing_prompt.txt",
        "industry": PROJECT_ROOT / "prompts" / "industry_score_prompt.txt",
        "all_a": PROJECT_ROOT / "prompts" / "all_a_score_prompt.txt",
        "style": PROJECT_ROOT / "prompts" / "style_score_prompt.txt",
    }
    catalog = PROJECT_ROOT / "data" / "sw2021_l2_industries.csv"
    for path in list(prompts.values()) + [catalog]:
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"缺失文件: {path}")

    if args.dry_run:
        settings = Settings.from_env(require_api_key=False)
        report = {
            "status": "ok",
            "api_called": False,
            "news_count": len(news_rows),
            "models": {
                "measure": settings.model_measure,
                "routing": settings.model_routing,
                "scoring": settings.model_scoring,
            },
            "stages": sorted(stages),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(output_dir / "dry_run_report.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.overwrite:
        for path in paths.values():
            path.unlink(missing_ok=True)
        for name in ("scores_relations.csv", "run_summary.json"):
            (output_dir / name).unlink(missing_ok=True)

    done_ids = load_done_ids(paths["measures"], key="news_id") if resume else set()
    todo = [n for n in news_rows if n["news_id"] not in done_ids]
    print(f"总计 {len(news_rows)}，已完成 {len(done_ids)}，待处理 {len(todo)}")

    settings = Settings.from_env(require_api_key=True)
    measure_llm = StructuredLLM(
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model_measure,
        timeout_seconds=settings.timeout_seconds,
        max_tokens=settings.max_tokens_measure,
        label="measure",
    )
    routing_llm = StructuredLLM(
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model_routing,
        timeout_seconds=settings.timeout_seconds,
        max_tokens=settings.max_tokens_routing,
        label="routing",
    )
    scoring_llm = StructuredLLM(
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model_scoring,
        timeout_seconds=settings.timeout_seconds,
        max_tokens=settings.max_tokens_scoring,
        label="scoring",
    )
    extractor = MeasureExtractor(measure_llm, prompts["measure"])
    router = MeasureRouter(routing_llm, prompts["routing"], catalog)
    scorer = RelationScorer(
        scoring_llm,
        industry_prompt=prompts["industry"],
        all_a_prompt=prompts["all_a"],
        style_prompt=prompts["style"],
        industry_catalog_path=catalog,
    )

    totals = {"measures": 0, "routes": 0, "score_calls": 0, "relations": 0, "errors": 0}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(
                process_one,
                news,
                extractor=extractor,
                router=router,
                scorer=scorer,
                stages=stages,
                paths=paths,
            ): news
            for news in todo
        }
        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="scoring pipeline",
        ):
            news = futures[future]
            try:
                stats = future.result()
                for k, v in stats.items():
                    totals[k] = totals.get(k, 0) + v
            except Exception as exc:
                totals["errors"] += 1
                _safe_append(
                    paths["errors"],
                    {"news_id": news["news_id"], "error": repr(exc)},
                )
                tqdm.write(f"[失败] {news['news_id']}: {exc}")

    relation_n = rebuild_csv(output_dir)
    summary = {
        "status": "completed",
        "input_news": len(news_rows),
        "todo_news": len(todo),
        "already_done": len(done_ids),
        "totals": totals,
        "relation_rows": relation_n,
        "llm": {
            "measure": measure_llm.stats(),
            "routing": routing_llm.stats(),
            "scoring": scoring_llm.stats(),
        },
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_dir / "run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if totals["errors"] == 0 else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        import traceback
        err_path = PROJECT_ROOT / "logs" / "fatal_error.log"
        err_path.parent.mkdir(parents=True, exist_ok=True)
        err_path.write_text(traceback.format_exc(), encoding="utf-8")
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
