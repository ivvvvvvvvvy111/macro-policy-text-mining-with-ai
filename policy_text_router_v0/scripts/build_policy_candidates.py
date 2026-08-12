from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_URL = "https://api-one.wallstcn.com/apiv1/content/lives"

ACTORS = [
    "国务院", "国常会", "中央政治局", "中央金融委员会", "人民银行", "央行", "证监会",
    "金融监管总局", "国家发展改革委", "发改委", "财政部", "商务部", "工业和信息化部",
    "工信部", "住房城乡建设部", "住建部", "国家能源局", "生态环境部", "国家卫生健康委",
    "教育部", "税务总局", "海关总署", "市场监管总局", "国家数据局", "国务院关税税则委员会",
    "美联储", "美国政府", "白宫", "美国商务部", "美国财政部", "欧盟委员会", "欧洲央行",
    "日本央行", "英国央行", "韩国央行", "印度央行",
]

ACTIONS = [
    "发布", "印发", "出台", "实施", "施行", "决定", "批准", "通过", "调整", "下调", "上调",
    "降低", "提高", "取消", "暂停", "恢复", "扩大", "缩减", "设立", "建立", "启动", "推出",
    "优化", "放宽", "收紧", "禁止", "限制", "豁免", "补贴", "征收", "减免", "加征", "制裁",
    "出口管制", "反倾销", "反补贴", "降息", "加息", "降准", "维持利率", "逆回购", "征求意见",
]

INSTRUMENTS = [
    "通知", "意见", "办法", "条例", "规定", "方案", "规划", "指导意见", "行动计划", "试点",
    "关税", "税率", "税收", "专项债", "特别国债", "再贷款", "再贴现", "LPR", "MLF", "公开市场操作",
    "交易制度", "融资融券", "IPO", "退市", "并购重组", "房地产", "限购", "首付比例", "消费券",
    "以旧换新", "排放标准", "能耗", "产能", "药品集采", "医保", "数据要素", "人工智能",
]

AGGREGATE_TITLE_TERMS = ["早餐", "盘前", "全球要闻", "要闻汇总", "收盘", "早报", "晚报", "直播中", "一图看懂"]

THEMES: dict[str, list[str]] = {
    "资本市场制度": ["证监会", "交易制度", "融资融券", "IPO", "退市", "并购重组", "上市公司"],
    "货币与金融": ["人民银行", "央行", "降准", "降息", "LPR", "MLF", "逆回购", "再贷款", "金融监管总局"],
    "财政与税收": ["财政部", "专项债", "特别国债", "税率", "税收", "减免", "政府采购"],
    "房地产": ["房地产", "住房", "住建部", "限购", "首付", "公积金", "房贷"],
    "消费与民生": ["消费", "以旧换新", "消费券", "教育", "养老", "就业", "育儿"],
    "科技与制造": ["工信部", "人工智能", "半导体", "机器人", "数据要素", "制造业", "设备更新"],
    "能源与环保": ["能源局", "新能源", "电力", "煤炭", "石油", "天然气", "排放", "能耗", "碳"],
    "医药医疗": ["卫健委", "医保", "药品集采", "医疗器械", "创新药"],
    "贸易与外部冲击": ["关税", "出口管制", "反倾销", "反补贴", "制裁", "商务部", "海关总署"],
    "海外宏观政策": ["美联储", "欧洲央行", "日本央行", "英国央行", "美国政府", "白宫", "欧盟委员会"],
}


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def score(text: str) -> int:
    actor_hits = sum(term in text for term in ACTORS)
    action_hits = sum(term in text for term in ACTIONS)
    instrument_hits = sum(term in text for term in INSTRUMENTS)
    return min(actor_hits, 2) * 3 + min(action_hits, 3) * 2 + min(instrument_hits, 3)


def theme(text: str) -> str:
    scores = {name: sum(term in text for term in terms) for name, terms in THEMES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "综合政策"


def fetch_items(max_pages: int, pause: float) -> list[dict]:
    cursor = None
    items: list[dict] = []
    seen: set[int] = set()
    for _ in range(max_pages):
        query = {"channel": "global-channel", "client": "pc", "limit": 100}
        if cursor:
            query["cursor"] = cursor
        url = BASE_URL + "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 policy-router-research"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))["data"]
        batch = data.get("items", [])
        for item in batch:
            if item.get("id") not in seen:
                items.append(item)
                seen.add(item.get("id"))
        cursor = data.get("next_cursor")
        if not batch or not cursor:
            break
        time.sleep(pause)
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="从公开快讯中筛选典型政策新闻候选")
    parser.add_argument("--max-pages", type=int, default=60)
    parser.add_argument("--count", type=int, default=150)
    parser.add_argument("--pause", type=float, default=0.15)
    parser.add_argument("--output", type=Path, default=Path("data/policy_candidates.csv"))
    args = parser.parse_args()

    rows = []
    for item in fetch_items(args.max_pages, args.pause):
        content = clean(item.get("content_text") or item.get("content") or "")
        title = clean(item.get("title") or "") or content[:70]
        text = title + " " + content
        if any(term in title for term in AGGREGATE_TITLE_TERMS) or len(content) > 1800:
            continue
        s = score(text)
        if s < 6 or not any(term in text for term in ACTORS) or not any(term in text for term in ACTIONS):
            continue
        dt = datetime.fromtimestamp(item["display_time"], ZoneInfo("Asia/Shanghai"))
        rows.append({
            "news_id": str(item["id"]), "title": title, "date": dt.isoformat(timespec="seconds"),
            "source": "华尔街见闻-7x24快讯", "url": item.get("uri", ""), "content": content,
            "candidate_theme": theme(text), "selection_score": s,
        })

    rows.sort(key=lambda x: (-int(x["selection_score"]), x["date"]), reverse=False)
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[row["candidate_theme"]].append(row)
    selected: list[dict] = []
    while len(selected) < args.count and any(buckets.values()):
        for name in THEMES.keys() | {"综合政策"}:
            if buckets[name] and len(selected) < args.count:
                selected.append(buckets[name].pop(0))
    if len(selected) < args.count:
        raise RuntimeError(f"仅筛得 {len(selected)} 条候选，请增加 --max-pages 或放宽规则。")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=selected[0].keys())
        writer.writeheader(); writer.writerows(selected)
    print(json.dumps({"fetched_candidates": len(rows), "written": len(selected), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
