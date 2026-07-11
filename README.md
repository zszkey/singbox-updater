# Sing-box 节点自动更新

通过 GitHub Actions 定时拉取订阅，自动生成 sing-box 配置。

## 使用

1. Fork 此仓库
2. 在 Settings → Secrets → Actions 添加 `SUB_URL`（你的订阅链接）
3. 每 6 小时自动更新，或点 Actions → 手动运行

## 本地拉取配置（Windows）

```bat
curl -sL -o config.json https://raw.githubusercontent.com/zszkey/singbox-updater/main/config.json
```
