#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.aggregate import (
    ALL_A_CHANNELS,
    DECAY_WINDOW_MULT,
    HALFLIFE_DAYS,
    build_all_a_panels,
    build_industry_panels,
    build_style_panels,
    load_events,
    sha256_file,
)
from src.io_utils import write_json


def write_csv(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def freeze_input(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
    digest = sha256_file(dst)
    (dst.with_suffix(dst.suffix + ".sha256")).write_text(digest + "\n", encoding="utf-8")
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build three-track daily factor panels")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "output" / "scores_relations.csv",
    )
    parser.add_argument(
        "--frozen",
        type=Path,
        default=ROOT / "data" / "frozen_scores_relations.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output" / "panels",
    )
    args = parser.parse_args()

    digest = freeze_input(args.input.resolve(), args.frozen.resolve())
    events = load_events(args.frozen.resolve())
    if not events:
        raise RuntimeError("冻结输入中没有可用关系事件")

    ind_ch, ind_daily, ind_min, ind_max = build_industry_panels(events)
    alla_ch, alla_daily, alla_min, alla_max = build_all_a_panels(events)
    style_daily, style_min, style_max = build_style_panels(events)

    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "industry_channel_daily.csv", ind_ch)
    write_csv(out / "industry_daily.csv", ind_daily)
    write_csv(out / "all_a_channel_daily.csv", alla_ch)
    write_csv(out / "all_a_daily.csv", alla_daily)
    write_csv(out / "style_axis_daily.csv", style_daily)

    track_counts = {"industry": 0, "all_a": 0, "style": 0}
    for e in events:
        track_counts[e.track] = track_counts.get(e.track, 0) + 1

    dates = [e.t0 for e in events]
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": "panels_v1",
        "calendar": "gregorian_v1",
        "decay": {
            "formula": "Signal = Score * 2^(-(t-t0)/HalfLife)",
            "half_life_days": HALFLIFE_DAYS,
            "window_mult": DECAY_WINDOW_MULT,
            "note": "baseline defaults; not backtested",
        },
        "scores": {
            "industry": "state_score",
            "all_a": "state_score",
            "style": "a_unit",
        },
        "all_a_channel_weights": {ch: 1.0 / len(ALL_A_CHANNELS) for ch in ALL_A_CHANNELS},
        "input": {
            "frozen_csv": str(args.frozen.resolve()),
            "source_csv": str(args.input.resolve()),
            "sha256": digest,
            "n_events_used": len(events),
            "track_counts": track_counts,
            "date_min": min(dates).isoformat(),
            "date_max": max(dates).isoformat(),
        },
        "outputs": {
            "industry_channel_daily_rows": len(ind_ch),
            "industry_daily_rows": len(ind_daily),
            "all_a_channel_daily_rows": len(alla_ch),
            "all_a_daily_rows": len(alla_daily),
            "style_axis_daily_rows": len(style_daily),
            "industry_date_span": [ind_min.isoformat(), ind_max.isoformat()] if ind_min else None,
            "all_a_date_span": [alla_min.isoformat(), alla_max.isoformat()] if alla_min else None,
            "style_date_span": [style_min.isoformat(), style_max.isoformat()] if style_min else None,
        },
        "exclusions": ["IC", "RankIC", "market_returns", "position_mapping"],
    }
    write_json(out / "panel_manifest.json", manifest)
    print(json.dumps(manifest["outputs"], ensure_ascii=False, indent=2))
    print(f"panels written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
