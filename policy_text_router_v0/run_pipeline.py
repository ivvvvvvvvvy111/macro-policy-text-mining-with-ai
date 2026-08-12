from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tqdm import tqdm

from src.config import PROJECT_ROOT, Settings
from src.io_utils import append_jsonl, read_news, write_csv, write_json
from src.llm_client import StructuredLLM
from src.measure_extract import MeasureExtractor
from src.routing import MeasureRouter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="政策新闻 measure 拆分与研究路由 v0.1")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "news_sample.csv")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "output")
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 条，建议首次用 3")
    parser.add_argument("--dry-run", action="store_true", help="只检查配置、数据和 prompt，不调用 API")
    parser.add_argument("--overwrite", action="store_true", help="覆盖本次输出文件")
    parser.add_argument("--workers", type=int, default=4, help="并发请求数，默认4")
    return parser.parse_args()


def flatten_result(news: dict[str, str], measure: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    industries_l2 = route["industries_l2"]
    return {
        "news_id": news["news_id"],
        "date": news["date"],
        "title": news["title"],
        "source": news["source"],
        "url": news["url"],
        "measure_id": measure["measure_id"],
        "measure_summary": measure["summary"],
        "policy_action": measure["policy_action"],
        "target": measure["target"],
        "mechanism": measure["mechanism"],
        "evidence": measure["evidence"],
        "all_a": route["all_a"],
        "style": route["style"],
        "industry": route["industry"],
        "style_dimensions": "|".join(route["style_dimensions"]),
        "industry_l2_codes": "|".join(item["industry_l2_code"] for item in industries_l2),
        "industry_l2_names": "|".join(item["industry_l2_name"] for item in industries_l2),
        "industry_l1_names": "|".join(item["industry_l1_name"] for item in industries_l2),
        "primary_route": route["primary_route"],
        "confidence": route["confidence"],
        "rationale": route["rationale"],
        "schema_version": route["schema_version"],
    }


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    news_rows = read_news(input_path, args.limit)
    if not news_rows:
        raise RuntimeError("输入文件中没有可处理的新闻。")

    measure_prompt = PROJECT_ROOT / "prompts" / "measure_prompt.txt"
    routing_prompt = PROJECT_ROOT / "prompts" / "routing_prompt.txt"
    industry_catalog = PROJECT_ROOT / "data" / "sw2021_l2_industries.csv"
    for path in (measure_prompt, routing_prompt, industry_catalog):
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"Prompt 文件缺失或为空: {path}")

    if args.dry_run:
        settings = Settings.from_env(require_api_key=False)
        report = {
            "status": "ok",
            "api_called": False,
            "input": str(input_path),
            "news_count": len(news_rows),
            "model": settings.model,
            "prompts": [str(measure_prompt), str(routing_prompt)],
            "industry_catalog": str(industry_catalog),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(output_dir / "dry_run_report.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    settings = Settings.from_env(require_api_key=True)
    llm = StructuredLLM(settings)
    extractor = MeasureExtractor(llm, measure_prompt)
    router = MeasureRouter(llm, routing_prompt, industry_catalog)

    measures_path = output_dir / "measures.jsonl"
    routes_path = output_dir / "routing_results.jsonl"
    errors_path = output_dir / "errors.jsonl"
    csv_path = output_dir / "routing_results.csv"
    if args.overwrite:
        for path in (measures_path, routes_path, errors_path, csv_path):
            path.unlink(missing_ok=True)
    elif any(path.exists() for path in (measures_path, routes_path, csv_path)):
        raise RuntimeError("输出已存在。若要重跑，请加 --overwrite。")

    flat_rows: list[dict[str, Any]] = []
    def process_one(news: dict[str, str]) -> tuple[dict[str, str], Any, list[tuple[Any, Any]]]:
        extraction = extractor.extract(news)
        routed = []
        for measure in extraction.measures:
            routed.append((measure, router.route(title=news["title"], measure=measure)))
        return news, extraction, routed

    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        future_map = {pool.submit(process_one, news): news for news in news_rows}
        iterator = concurrent.futures.as_completed(future_map)
        for future in tqdm(iterator, total=len(future_map), desc="处理新闻"):
            news = future_map[future]
            completed += 1
            try:
                news, extraction, routed = future.result()
                extraction_record = {"news": news, "result": extraction.model_dump()}
                append_jsonl(measures_path, extraction_record)
                for measure, route in routed:
                    route_record = {
                        "news_id": news["news_id"],
                        "title": news["title"],
                        "measure": measure.model_dump(),
                        "routing": route.model_dump(),
                    }
                    append_jsonl(routes_path, route_record)
                    flat_rows.append(flatten_result(news, measure.model_dump(), route.model_dump()))
            except Exception as exc:
                append_jsonl(errors_path, {"news_id": news["news_id"], "error": repr(exc)})
                tqdm.write(f"[失败] {news['news_id']}: {exc}")

    write_csv(csv_path, flat_rows)
    summary = {
        "status": "completed",
        "input_news": len(news_rows),
        "completed_news": completed,
        "policy_news": sum(1 for line in measures_path.read_text(encoding="utf-8").splitlines() if '"is_policy_news": true' in line),
        "measures": len(flat_rows),
        "errors": len(errors_path.read_text(encoding="utf-8").splitlines()) if errors_path.exists() else 0,
        "llm": llm.stats(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_dir / "run_summary.json", summary)
    print(f"完成：{len(news_rows)} 条新闻，{len(flat_rows)} 条 measure 路由结果。")
    print(f"结果目录：{output_dir}")
    return 0 if flat_rows or not errors_path.exists() else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
