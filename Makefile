.PHONY: status long-run-status calendar-report test safety-check docs-check delivery-check check

status:
	@python3 tools/project_status.py

long-run-status:
	@python3 tools/calendar_run_status.py

calendar-report:
	@work_scoring_v1/.venv/bin/python tools/build_calendar_final_report_v2.py

test:
	@if test -x work_scoring_v1/.venv/bin/python; then cd work_scoring_v1 && .venv/bin/python -m pytest -q; elif python3 -c "import pytest" 2>/dev/null; then cd work_scoring_v1 && python3 -m pytest -q; else echo "SKIP: 当前Python环境未安装pytest；安装work_scoring_v1/requirements.txt后运行make test"; fi

safety-check:
	@python3 tools/repository_check.py

docs-check:
	@test -f AGENTS.md
	@test -f CONSTRAINTS.md
	@test -f DECISIONS.md
	@test -f PROGRESS.md
	@test -f policy_text_router_v0/README.md
	@test -f work_scoring_v1/README.md
	@test -f state/README.md
	@test -f deliverables/README.md

delivery-check:
	@test -s deliverables/结果展示网页/index.html
	@test -s deliverables/长文政策因子最终报告/index.html
	@test -s deliverables/政策新闻信息提取全流程报告.md
	@python3 -c "from pathlib import Path; s=Path('deliverables/结果展示网页/index.html').read_text(); assert '原始新闻如何经过 Prompt 变成分数' in s and '最终分数' in s"

check: safety-check docs-check test delivery-check status
