from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="获取申万2021二级行业字典")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "sw2021_l2_industries.csv",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=ROOT / "data" / "sw2021_l2_industries.summary.json",
    )
    args = parser.parse_args()

    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("请先安装依赖: python -m pip install akshare") from exc

    frame = ak.sw_index_second_info()
    required = {"行业代码", "行业名称", "上级行业"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"行业接口缺少字段: {sorted(missing)}")

    output = pd.DataFrame(
        {
            "industry_l2_code": frame["行业代码"].astype(str).str.replace(".SI", "", regex=False),
            "industry_l2_name": frame["行业名称"].astype(str).str.strip(),
            "industry_l1_name": frame["上级行业"].astype(str).str.strip(),
            "classification_version": "SW2021",
            "source": "AKShare.sw_index_second_info",
        }
    ).drop_duplicates(subset=["industry_l2_code"])
    output = output.sort_values(["industry_l1_name", "industry_l2_code"]).reset_index(drop=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    summary = {
        "classification_version": "SW2021",
        "level": "L2",
        "retrieved_count": int(len(output)),
        "standard_reference_count": 134,
        "is_reference_count_complete": len(output) == 134,
        "note": (
            "公开接口可能只返回当前存在数据的行业。程序保留完整性告警，"
            "正式生产前应使用公司持有的申万授权字典进行最终核对。"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output": str(args.output),
    }
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
