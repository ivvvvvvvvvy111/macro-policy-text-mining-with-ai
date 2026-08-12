from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "work_scoring_v1" / "data"
OUT = ROOT / "work_scoring_v1" / "output"
DELIVERY = ROOT / "deliverables"


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def text(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return v


def main():
    DELIVERY.mkdir(exist_ok=True)
    with (DATA / "sample_5000.csv").open(encoding="utf-8-sig") as f:
        news = list(csv.DictReader(f))
    measure_records = read_jsonl(OUT / "measures.jsonl")
    routing = read_jsonl(OUT / "routing_results.jsonl")
    errors = read_jsonl(OUT / "errors.jsonl")
    with (OUT / "scores_relations.csv").open(encoding="utf-8-sig") as f:
        relations = list(csv.DictReader(f))

    news_by_id = {x["news_id"]: x for x in news}
    measure_result_by_news = {x["news"]["news_id"]: x["result"] for x in measure_records}
    error_messages = defaultdict(list)
    for e in errors:
        error_messages[e.get("news_id", "未知")].append(e.get("error", ""))

    route_by_key = {}
    routes_by_news = defaultdict(list)
    for x in routing:
        key = (x["news_id"], x["measure"]["measure_id"])
        route_by_key[key] = x
        routes_by_news[x["news_id"]].append(x)

    rel_by_key = defaultdict(list)
    rel_by_news = defaultdict(list)
    for x in relations:
        key = (x["news_id"], x["measure_id"])
        rel_by_key[key].append(x)
        rel_by_news[x["news_id"]].append(x)

    overview = []
    for n in news:
        nid = n["news_id"]
        mr = measure_result_by_news.get(nid)
        rs = routes_by_news.get(nid, [])
        rels = rel_by_news.get(nid, [])
        if mr is None:
            status = "模型失败/无拆分结果" if nid in error_messages else "未处理/缺失"
            is_policy, mcount, event_summary, exclusion = "", 0, "", ""
        else:
            is_policy = mr.get("is_policy_news", False)
            mcount = len(mr.get("measures", []))
            event_summary = mr.get("event_summary", "")
            exclusion = mr.get("exclusion_reason", "")
            if not is_policy:
                status = "已判定非政策新闻"
            elif not rs:
                status = "已拆分但路由缺失"
            elif not rels and any(any(x["routing"].get(t) for t in ("all_a", "style", "industry")) for x in rs):
                status = "已路由但无评分关系"
            else:
                status = "已完成"
        track_set = sorted({x["track"] for x in rels})
        overview.append([
            nid, n["event_id"], n["date"], n["title"], n["source"], n["url"],
            n["content_status"], float(n["rule_score"]) if n["rule_score"] else None,
            text(is_policy), mcount, len(rs), len(rels), "、".join(track_set), status,
            len(error_messages.get(nid, [])), event_summary, exclusion, n["content"],
        ])

    measure_rows = []
    for x in routing:
        nid = x["news_id"]
        m, r = x["measure"], x["routing"]
        inds = r.get("industries_l2", [])
        key = (nid, m["measure_id"])
        measure_rows.append([
            nid, news_by_id.get(nid, {}).get("date", ""), x.get("title", ""), m["measure_id"],
            m.get("summary", ""), m.get("policy_action", ""), m.get("target", ""),
            m.get("mechanism", ""), m.get("evidence", ""), text(r.get("all_a")),
            text(r.get("style")), text(r.get("industry")), r.get("primary_route", ""),
            "、".join(r.get("style_dimensions", [])),
            "；".join(f'{i.get("industry_l2_code","")} {i.get("industry_l2_name","")}（{i.get("industry_l1_name","")}）' for i in inds),
            r.get("confidence"), r.get("rationale", ""), len(rel_by_key.get(key, [])),
            "有错误记录" if nid in error_messages else "",
        ])

    relation_headers = [
        "路线", "新闻ID", "日期", "标题", "来源", "原文链接", "措施ID", "措施摘要", "关系ID",
        "渠道", "期限/生效速度", "风格轴", "行业二级代码", "行业二级名称", "行业一级名称", "直接性",
        "方向", "强度", "相对强度", "覆盖", "确定性", "持续性", "信息增量", "政策变化", "新颖度",
        "置信度", "状态分", "新闻分", "A单元", "意外度", "空值原因", "证据", "评分理由", "主路由", "路由置信度"
    ]
    relation_keys = [
        "track", "news_id", "date", "title", "source", "url", "measure_id", "measure_summary", "relation_id",
        "channel", "horizon", "style_axis", "industry_l2_code", "industry_l2_name", "industry_l1_name", "directness",
        "direction", "intensity", "relative_strength", "coverage", "certainty", "persistence", "info_increment",
        "policy_delta", "novelty", "confidence", "state_score", "news_score", "a_unit", "surprise", "null_reason",
        "evidence", "rationale", "routing_primary", "routing_confidence"
    ]
    numeric = {"direction", "intensity", "relative_strength", "coverage", "certainty", "persistence", "info_increment", "policy_delta", "novelty", "confidence", "state_score", "news_score", "a_unit", "surprise", "routing_confidence"}
    relation_rows = []
    for r in relations:
        row = []
        for k in relation_keys:
            v = r.get(k, "")
            if k in numeric and v not in (None, ""):
                try: v = float(v)
                except ValueError: pass
            row.append(v)
        relation_rows.append(row)

    error_rows = []
    for i, e in enumerate(errors, 1):
        nid = e.get("news_id", "")
        n = news_by_id.get(nid, {})
        error_rows.append([i, nid, n.get("date", ""), n.get("title", ""), e.get("error", "")])

    groups = defaultdict(list)
    for (nid, mid), rs in rel_by_key.items():
        tracks = frozenset(r["track"] for r in rs)
        route = route_by_key.get((nid, mid))
        if not route:
            continue
        confidence = float(route["routing"].get("confidence", 0))
        candidate = (confidence, len(rs), nid, mid, route, rs)
        for t in tracks:
            groups[t].append(candidate)
        if len(tracks) == 3:
            groups["multi"].append(candidate)

    examples = []
    used = set()
    for category, count in (("all_a", 3), ("style", 3), ("industry", 3), ("multi", 3)):
        candidates = sorted(groups[category], key=lambda z: (z[0], z[1]), reverse=True)
        picked = 0
        for conf, nrels, nid, mid, route, rs in candidates:
            key = (nid, mid)
            if key in used and category != "multi":
                continue
            used.add(key)
            picked += 1
            m = route["measure"]
            tracks = sorted({r["track"] for r in rs})
            score_summary = "；".join(
                f'{r["track"]}:{r["channel"]}' +
                (f'/{r["style_axis"]}' if r.get("style_axis") else "") +
                (f'/{r["industry_l2_name"]}' if r.get("industry_l2_name") else "") +
                f'/方向{r.get("direction","")}' for r in rs[:6]
            )
            examples.append([
                ("三路线同时" if category == "multi" else category), nid, news_by_id[nid]["date"], news_by_id[nid]["title"], mid,
                m["summary"], "、".join(tracks), route["routing"]["primary_route"], conf,
                route["routing"]["rationale"], nrels, score_summary, news_by_id[nid]["url"],
            ])
            if picked >= count:
                break

    prompts = []
    for stage, filename in [
        ("措施拆分", "measure_prompt.txt"), ("措施路由", "routing_prompt.txt"),
        ("全A评分", "all_a_score_prompt.txt"), ("风格评分", "style_score_prompt.txt"),
        ("行业评分", "industry_score_prompt.txt")]:
        prompts.append([stage, filename, (ROOT / "work_scoring_v1" / "prompts" / filename).read_text(encoding="utf-8")])

    status_counts = Counter(r[13] for r in overview)
    unique_error_news = len(error_messages)
    track_counts = Counter(r[0] for r in relation_rows)
    route_counts = Counter(r[12] for r in measure_rows)
    summary = {
        "input_news": len(news), "measure_output_news": len(measure_records),
        "routing_rows": len(routing), "relation_rows": len(relations),
        "error_log_rows": len(errors), "unique_error_news": unique_error_news,
        "status_counts": dict(status_counts), "track_counts": dict(track_counts),
        "route_counts": dict(route_counts), "examples": examples,
    }
    payload = {
        "summary": summary,
        "overview_headers": ["新闻ID", "事件ID", "日期", "标题", "来源", "原文链接", "正文状态", "规则分", "是否政策新闻", "措施数", "路由措施数", "评分关系数", "评分路线", "处理状态", "错误日志数", "事件摘要", "排除原因", "原始正文"],
        "overview_rows": overview,
        "measure_headers": ["新闻ID", "日期", "标题", "措施ID", "措施摘要", "政策动作", "作用对象", "直接机制", "原文证据", "全A", "风格", "行业", "主路由", "风格维度", "申万二级行业", "路由置信度", "路由理由", "评分关系数", "质量标记"],
        "measure_rows": measure_rows,
        "relation_headers": relation_headers, "relation_rows": relation_rows,
        "error_headers": ["序号", "新闻ID", "日期", "标题", "错误信息"], "error_rows": error_rows,
        "example_headers": ["案例类别", "新闻ID", "日期", "标题", "措施ID", "措施摘要", "实际评分路线", "主路由", "路由置信度", "路由理由", "关系数", "评分摘要", "原文链接"],
        "example_rows": examples,
        "prompt_headers": ["环节", "文件", "提示词全文"], "prompt_rows": prompts,
    }
    (DELIVERY / "policy_pipeline_delivery.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
