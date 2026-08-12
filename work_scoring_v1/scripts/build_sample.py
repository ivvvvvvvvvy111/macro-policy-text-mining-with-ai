#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROJECT_ROOT, REPO_ROOT
from src.sample_builder import build_sample


def main() -> int:
    parser = argparse.ArgumentParser(description="抽取 TopN 政策新闻样本并对齐正文")
    parser.add_argument(
        "--candidates",
        type=Path,
        default=REPO_ROOT / "exports" / "policy_event_candidates.csv",
    )
    parser.add_argument("--state-dir", type=Path, default=REPO_ROOT / "state")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "sample_5000.csv",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "data" / "sample_manifest.json",
    )
    parser.add_argument("--n", type=int, default=5000)
    args = parser.parse_args()

    manifest = build_sample(
        candidates_csv=args.candidates,
        state_dir=args.state_dir,
        output_csv=args.output,
        manifest_path=args.manifest,
        target_n=args.n,
    )
    print(
        f"抽样完成: selected={manifest['selected_n']} "
        f"pool={manifest['candidate_pool_after_filter']} "
        f"skipped_no_content={manifest['skipped_no_content']}"
    )
    print(f"输出: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
