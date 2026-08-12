from __future__ import annotations

import csv
import json
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
VALID_L1_INDUSTRIES = {
    "农林牧渔", "基础化工", "钢铁", "有色金属", "电子", "汽车", "家用电器", "食品饮料", "纺织服饰",
    "轻工制造", "医药生物", "公用事业", "交通运输", "房地产", "商贸零售", "社会服务", "银行",
    "非银金融", "综合", "建筑材料", "建筑装饰", "电力设备", "机械设备", "国防军工", "计算机",
    "传媒", "通信", "煤炭", "石油石化", "环保", "美容护理",
}


def load_l2_catalog() -> dict[str, str]:
    path = ROOT / "data" / "sw2021_l2_industries.csv"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["industry_l2_code"]: row["industry_l2_name"] for row in csv.DictReader(f)}


def industry_values(route: dict) -> tuple[list[str], list[str]]:
    if "industries_l2" in route:
        return (
            [item["industry_l2_code"] for item in route["industries_l2"]],
            [item["industry_l2_name"] for item in route["industries_l2"]],
        )
    return ([], list(route.get("industries", [])))


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    with (ROOT / "data" / "news_sample.csv").open("r", encoding="utf-8-sig", newline="") as f:
        news_rows = list(csv.DictReader(f))
    news_by_id = {row["news_id"]: row for row in news_rows}
    order = {row["news_id"]: i + 1 for i, row in enumerate(news_rows)}
    measures = jsonl(OUTPUT / "measures.jsonl")
    routes = jsonl(OUTPUT / "routing_results.jsonl")
    errors = jsonl(OUTPUT / "errors.jsonl") if (OUTPUT / "errors.jsonl").exists() else []
    valid_l2 = load_l2_catalog()

    invariant_errors = []
    invalid_industries = []
    for item in routes:
        r = item["routing"]
        count = sum((r["all_a"], r["style"], r["industry"]))
        expected = "none" if count == 0 else "multiple" if count > 1 else next(k for k in ("all_a", "style", "industry") if r[k])
        industry_codes, industry_names = industry_values(r)
        has_industry_values = bool(industry_codes or industry_names)
        if r["primary_route"] != expected or r["style"] != bool(r["style_dimensions"]) or r["industry"] != has_industry_values:
            invariant_errors.append(f"{item['news_id']}:{item['measure']['measure_id']}")
        if r.get("schema_version") == "routing.v2":
            invalid_industries.extend(code for code in industry_codes if code not in valid_l2)
        else:
            invalid_industries.extend(value for value in industry_names if value not in VALID_L1_INDUSTRIES)

    all_measures = [(item["news"], m) for item in measures for m in item["result"]["measures"]]
    evidence_exact = sum(m["evidence"] in (news["title"] + "\n" + news["content"]) for news, m in all_measures)
    near_duplicates = 0
    for item in measures:
        ms = item["result"]["measures"]
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                if SequenceMatcher(None, ms[i]["summary"], ms[j]["summary"]).ratio() >= 0.82:
                    near_duplicates += 1

    combos = Counter(
        "+".join(k for k in ("all_a", "style", "industry") if item["routing"][k]) or "none"
        for item in routes
    )
    summary = {
        "news_input": len(news_rows),
        "news_output": len(measures),
        "policy_news": sum(item["result"]["is_policy_news"] for item in measures),
        "measure_count": len(routes),
        "api_or_pipeline_errors": len(errors),
        "evidence_exact_match": evidence_exact,
        "evidence_exact_match_rate": round(evidence_exact / len(all_measures), 4) if all_measures else 0,
        "schema_invariant_errors": len(invariant_errors),
        "invalid_industry_labels": sorted(set(invalid_industries)),
        "near_duplicate_measure_pairs": near_duplicates,
        "route_combinations": dict(combos),
        "label_positive_counts": {
            "all_a": sum(item["routing"]["all_a"] for item in routes),
            "style": sum(item["routing"]["style"] for item in routes),
            "industry": sum(item["routing"]["industry"] for item in routes),
        },
        "primary_route_counts": dict(Counter(item["routing"]["primary_route"] for item in routes)),
        "style_dimension_counts": dict(Counter(v for item in routes for v in item["routing"]["style_dimensions"])),
        "industry_counts": dict(
            Counter(name for item in routes for name in industry_values(item["routing"])[1]).most_common()
        ),
        "theme_news_counts": dict(Counter(row.get("candidate_theme", "") for row in news_rows)),
        "measure_count_per_news": dict(Counter(len(item["result"]["measures"]) for item in measures)),
        "confidence": {
            "min": min((item["routing"]["confidence"] for item in routes), default=None),
            "mean": round(sum(item["routing"]["confidence"] for item in routes) / len(routes), 4) if routes else None,
            "max": max((item["routing"]["confidence"] for item in routes), default=None),
        },
    }
    (OUTPUT / "qa_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    review = []
    for item in sorted(routes, key=lambda x: (order[x["news_id"]], x["measure"]["measure_id"])):
        news = news_by_id[item["news_id"]]; m = item["measure"]; r = item["routing"]
        review.append({
            "sample_order": order[item["news_id"]], "news_id": item["news_id"],
            "theme": news.get("candidate_theme", ""), "date": news["date"], "source": news["source"],
            "title": news["title"], "content": news["content"], "url": news["url"],
            "measure_id": m["measure_id"], "measure_summary": m["summary"], "evidence": m["evidence"],
            "all_a": r["all_a"], "style": r["style"], "industry": r["industry"],
            "style_dimensions": "|".join(r["style_dimensions"]),
            "industry_l2_codes": "|".join(industry_values(r)[0]),
            "industry_l2_names": "|".join(industry_values(r)[1]),
            "primary_route": r["primary_route"], "confidence": r["confidence"], "rationale": r["rationale"],
        })
    write_csv(OUTPUT / "results_for_review.csv", review)

    annotation = []
    for row in review:
        annotation.append({
            **row,
            "human_measure_valid": "", "human_all_a": "", "human_style": "", "human_industry": "",
            "human_correct_industry_l2_codes": "", "human_error_type": "", "human_notes": "",
        })
    write_csv(ROOT / "data" / "human_annotation_template.csv", annotation)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if len(news_rows) != 50 or len(measures) != 50 or errors or evidence_exact != len(all_measures) or invariant_errors or invalid_industries:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
