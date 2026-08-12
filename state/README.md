# state

本目录保存各新闻源的SQLite采集状态库，仅用于本地运行，不提交Git。

每个库通常包含：
- `records`：标题、正文、URL、发布时间、正文状态和原始载荷。
- `checkpoints`：采集流的游标与更新时间。
- `collection_errors`：采集阶段错误和上下文。

主要文件包括 `official.sqlite3`、`wallstreetcn.sqlite3`、`sina_finance.sqlite3`、`cls.sqlite3`、`daily_updates.sqlite3` 和 `archive_index.sqlite3`。

读取建议：使用Navicat Premium Lite或DBeaver，以只读连接打开。不要在Git中存储这些数据库及其WAL/SHM文件。
