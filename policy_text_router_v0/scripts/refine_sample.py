from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "news_sample.csv"
CANDIDATES = ROOT / "data" / "policy_candidates.csv"
LOG = ROOT / "work" / "curation" / "manual_refinement.json"

# 删除“仅在考虑中的改革”、低A股相关性的海外社会政策、重复央行事件和重复个案监管；
# 换入行动更明确、研究路由更典型的行业、消费与制度政策。
REPLACEMENTS = {
    "3143464": ("3144029", "删除尚未落地的美联储会议频率设想；换入核电装机规划"),
    "3140828": ("3138580", "删除A股映射较弱的奥地利社交媒体法案；换入北京以旧换新补贴"),
    "3138907": ("3140770", "删除以官员风险评估为主的欧洲央行表态；换入基层中医药服务规划"),
    "3142891": ("3141031", "删除与另一条日本央行会议新闻重复的利率决议；换入汽车供应商账期规范"),
    "3143159": ("3139444", "删除重复的单一券商监管个案；换入综合交通体系改革"),
    "3143070": ("3140182", "删除仅有未来可能性表态的日本央行要点；换入已正式发布的行政复议程序规定"),
    "3145757": ("3141549", "删除仍处于研究阶段的住房提振举措；换入已发布的智能家电质量安全国家标准"),
    "3142874": ("3138508", "删除仍在研究制定的扩大内需方案；换入已明确开工规模的海上风电规划"),
    "3142877": ("3143231", "删除只有方向性表态的宏观政策新闻；换入已核准的核电项目"),
    "3141750": ("3139413", "删除原则性央企科技部署；换入住建部已明确的建筑市场监管措施"),
}


def load(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def main() -> None:
    sample = load(SAMPLE)
    candidates = {row["news_id"]: row for row in load(CANDIDATES)}
    old_ids = {row["news_id"] for row in sample}
    log = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []
    for index, row in enumerate(sample):
        if row["news_id"] not in REPLACEMENTS:
            continue
        new_id, reason = REPLACEMENTS[row["news_id"]]
        if new_id in old_ids:
            raise RuntimeError(f"替换目标已在样本中: {new_id}")
        new = dict(candidates[new_id])
        new["curation_quality_score"] = "refined"
        log.append({"position": index + 1, "removed": row["news_id"], "added": new_id, "reason": reason})
        sample[index] = new
    if len(sample) != 50 or len({row["news_id"] for row in sample}) != 50:
        raise RuntimeError("精修后样本数量或唯一性异常")
    with SAMPLE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(sample[0].keys()))
        writer.writeheader(); writer.writerows(sample)
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"replaced": len(log), "sample_count": len(sample)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
