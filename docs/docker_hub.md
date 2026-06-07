# Docker Hub镜像发布与VPS拉取

本仓库已经配置 GitHub Actions，可以在推送 `main` 分支或手动运行 workflow 时，自动构建并推送 Docker Hub 镜像。

## 配置Docker Hub Secrets

在 Docker Hub 创建访问令牌：

1. 登录 Docker Hub。
2. 进入 `Account Settings`。
3. 打开 `Personal access tokens`。
4. 创建一个具有读写权限的 token。

在 GitHub 仓库配置 secrets：

1. 打开 `https://github.com/yeah1z1/tiktok`。
2. 进入 `Settings` -> `Secrets and variables` -> `Actions`。
3. 新增两个 Repository secrets：
   - `DOCKERHUB_USERNAME`: 你的 Docker Hub 用户名。
   - `DOCKERHUB_TOKEN`: Docker Hub personal access token。

配置完成后，到 GitHub 仓库的 `Actions` 页面，手动运行 `Publish Docker image`，或者直接推送一次 `main` 分支。

## 镜像名称

如果你的 Docker Hub 用户名是 `yourname`，镜像会发布为：

```text
yourname/tiktok:latest
yourname/tiktok:<git-version>
```

## VPS拉取运行

```bash
docker pull yourname/tiktok:latest
```

运行 API 服务：

```bash
docker run -d \
  --name tiktok \
  --restart unless-stopped \
  --network host \
  -e TZ=Asia/Shanghai \
  -e TIKTOK_COOKIE='你的TikTok Cookie' \
  -v "$(pwd)/outputs:/app/outputs" \
  yourname/tiktok:latest
```

访问：

```text
http://你的VPS_IP/docs
```

运行关键词热点抓取：

```bash
docker exec -it tiktok python tools/tiktok_hot_videos.py \
  --keywords "ai tools,fitness" \
  --pages 2 \
  --count 20 \
  --limit 20 \
  --sort-by hot \
  --output outputs/tiktok_hot_videos.json \
  --csv-output outputs/tiktok_hot_videos.csv
```

如果 TikTok 在你的 VPS 网络环境无法访问，请增加代理环境变量：

```bash
-e TIKTOK_HTTP_PROXY='http://代理地址:端口' \
-e TIKTOK_HTTPS_PROXY='http://代理地址:端口'
```
