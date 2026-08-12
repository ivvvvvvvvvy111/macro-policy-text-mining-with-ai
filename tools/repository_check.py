from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {".env", "id_rsa", "id_ed25519"}
FORBIDDEN_DIRS = {"postgres_data", "backups", "node_modules", ".venv"}
MAX_TRACKED_CANDIDATE = 20 * 1024 * 1024
IGNORED_LARGE_PREFIXES = (
    "state/", "deliverables/", "work_scoring_v1/output/",
    "work_scoring_v1/data/sample_5000.csv", "work_scoring_v1/data/frozen_scores_relations.csv",
)


def main() -> None:
    problems: list[str] = []
    for base, dirs, files in os.walk(ROOT):
        rel_base = Path(base).relative_to(ROOT)
        dirs[:] = [d for d in dirs if d not in FORBIDDEN_DIRS and d != ".git"]
        for name in files:
            path = Path(base) / name
            rel = path.relative_to(ROOT)
            if name in FORBIDDEN_NAMES:
                problems.append(f"敏感配置存在（必须被gitignore排除）: {rel}")
            if path.stat().st_size > MAX_TRACKED_CANDIDATE and not str(rel).startswith(IGNORED_LARGE_PREFIXES):
                problems.append(f"需人工确认的大文件: {rel}")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    required = ["**/.env", "postgres_data/", "state/*.sqlite3", "logs/", "work_scoring_v1/output/"]
    missing = [x for x in required if x not in gitignore]
    if missing:
        problems.append(".gitignore 缺少规则: " + ", ".join(missing))
    actionable = [p for p in problems if not p.startswith("敏感配置存在")]
    print("仓库安全检查")
    for p in problems:
        print(f"- {p}")
    if actionable:
        raise SystemExit(1)
    print("- 通过：敏感配置由.gitignore保护，未发现未处理的大文件风险")


if __name__ == "__main__":
    main()
