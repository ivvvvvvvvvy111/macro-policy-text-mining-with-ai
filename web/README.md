# 宏观政策研究台 Web 前端

这个目录是宏观政策研究台的可部署网页源码，用于替代 ChatGPT Sites 私有链接，方便同事、Claude、Cursor 或其他 AI 直接从 GitHub 读取和修改。

## 线上数据来源

网页读取 Supabase：

- `macro_dashboard_artifacts`：v5 展示层 payload
- `macro_market_returns`：ZZVD 行情
- `macro_barra_returns`：Barra 风格
- `macro_job_runs`：同步任务日志
- `macro_role_requests`：研究员权限申请
- 管理员 RPC：`macro_admin_list_users()` / `macro_admin_set_user_role()`

前端只包含 Supabase publishable key。不要把 service role key、FQuant 密码、模型 API Key 写进本目录。

## 本地预览

```bash
cd web
python3 -m http.server 8766
```

然后打开：

```text
http://localhost:8766
```

## Vercel 部署

推荐在 Vercel 中选择本仓库，并设置：

```text
Framework Preset: Other
Root Directory: web
Build Command: 留空
Output Directory: .
Install Command: 留空
```

也可以在本地登录 Vercel 后运行：

```bash
cd web
vercel --prod
```

## 权限逻辑

- 未登录：不能读业务数据。
- 已登录但没有 `macro_role`：默认 viewer。
- `viewer`：看结果页、图表和证据导图，不能下载底表。
- `researcher`：看原文、措施、因子、图表，后续可开放筛选下载。
- `admin`：看日志、用户权限、下载审计，并能修改用户角色。

## 给其他 AI 的修改入口

如果要改网页长相，优先改：

```text
web/index.html
```

当前是单文件静态页，便于 Claude / Cursor / Codex 直接修改。后续如果 UI 复杂起来，可以再拆成 React/Next.js 项目。
