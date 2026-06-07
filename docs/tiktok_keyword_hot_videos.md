# TikTok关键词热点视频抓取

这个项目已经新增 TikTok 关键词搜索与热点视频排序能力，适合按指定关键词抓取公开 TikTok 作品数据，并导出 JSON/CSV 供后续分析。

## 运行前准备

TikTok Web 接口对 Cookie、地区和代理比较敏感。优先使用环境变量传入敏感信息，避免把自己的 Cookie 写入仓库：

```powershell
$env:TIKTOK_COOKIE="你的 TikTok Cookie"
$env:TIKTOK_HTTP_PROXY="http://127.0.0.1:7890"
$env:TIKTOK_HTTPS_PROXY="http://127.0.0.1:7890"
```

也可以直接修改 `crawlers/tiktok/web/config.yaml` 里的 TikTok Cookie 和代理配置。

## CLI抓取

安装依赖：

```powershell
pip install -r requirements.txt
```

按关键词抓取热点视频，并导出 JSON 和 CSV：

```powershell
python tools/tiktok_hot_videos.py `
  --keywords "ai tools,fitness" `
  --pages 2 `
  --count 20 `
  --limit 20 `
  --sort-by hot `
  --output outputs/tiktok_hot_videos.json `
  --csv-output outputs/tiktok_hot_videos.csv
```

常用参数：

- `--keywords`: 关键词，支持空格分隔或逗号分隔。
- `--pages`: 每个关键词抓取页数。
- `--count`: 每页数量。
- `--limit`: 每个关键词保留多少条结果。
- `--global-limit`: 多关键词合并后保留多少条结果。
- `--sort-by`: 排序字段，支持 `hot`、`play`、`like`、`comment`、`share`、`collect`、`create_time`。
- `--include-photos`: 默认只保留视频；加上该参数会包含图文作品。
- `--include-raw`: 在 JSON 中保留 TikTok 原始响应，便于调试。
- `--fail-fast`: 默认某个关键词失败会继续处理其它关键词，并把错误写入 JSON 的 `errors` 字段；加上该参数会在首次失败时退出。

热点排序默认使用综合分：

```text
hot_score = play_count + digg_count * 8 + comment_count * 12 + share_count * 16 + collect_count * 10
```

## API调用

启动服务：

```powershell
python start.py
```

原始关键词搜索：

```text
GET /api/tiktok/web/fetch_keyword_search?keyword=ai%20tools&count=20
```

标准化热点视频列表：

```text
GET /api/tiktok/web/fetch_keyword_hot_videos?keyword=ai%20tools&pages=2&count=20&limit=20&sort_by=hot
```

## 合规提示

请只抓取公开数据，控制请求频率，并遵守 TikTok 服务条款、当地法律法规和内容版权要求。这个功能用于学习、分析和自动化整理，不建议用于高频采集或绕过平台限制。
