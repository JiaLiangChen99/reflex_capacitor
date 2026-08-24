# CI：Android debug APK

GitHub Actions 按 **Environment** 烘焙不同后端 URL，打 debug APK。

## 配置 GitHub Environments

仓库 **Settings → Environments** 新建三个环境，各添加 **Environment secret**：

| Environment | Secret | 示例值 | 说明 |
|-------------|--------|--------|------|
| `lan` | `REFLEX_BACKEND_URL` | `http://192.168.1.56:8001` | 局域网 HTTP，需 cleartext + `androidScheme: http` |
| `staging` | `REFLEX_BACKEND_URL` | `https://staging.example.com` | HTTPS + WSS |
| `production` | `REFLEX_BACKEND_URL` | `https://api.example.com` | HTTPS + WSS |

**不要**在 workflow 里写死后端 IP；push 时只构建 `lan`，手动 Run workflow 可选单个环境或 `all`（三个 matrix 并行）。

## 触发方式

| 事件 | 构建矩阵 |
|------|----------|
| push / PR → `main` | 仅 `lan` |
| workflow_dispatch | 选 `lan` / `staging` / `production` / `all` |

Actions → **Android APK** → Run workflow。

## CI 校验项

**HTTP（lan）**

- baked env 含 `ws://<host>/_event`
- `server.cleartext: true`、`androidScheme: "http"`
- Manifest `usesCleartextTraffic="true"`

**HTTPS（staging / production）**

- baked env 含 `wss://<host>/_event`
- `androidScheme: "https"`，且 `cleartext` 不为 `true`

**共用**

- `index.html` 已注入 `<!-- reflex-capacitor bridge begin -->`
- `pytest tests/` 通过后再打 APK

## 真机调试（lan）

### WebSocket timeout

1. **混合内容**：HTTP 后端必须 `androidScheme: "http"`（插件已自动设置）。
2. **防火墙**：手机访问不了 `http://<ip>:8001/ping` 时，在 Windows 放行 Python 入站（如 TCP 8001）。

### 本地后端

```bash
reflex run --env prod --backend-only --backend-host 0.0.0.0 --backend-port 8001
```

手机浏览器应能打开：`http://<你的局域网IP>:8001/ping` → `pong`。

## 下载 APK

构建完成后 → 对应 job → **Artifacts** → `app-debug-lan`（或 staging / production）。

## Release AAB（可选）

Workflow **Android Release AAB**（仅 `workflow_dispatch`）打 **signed AAB**，用于 Google Play。

**Environment：`production`** 需配置：

| Secret | 说明 |
|--------|------|
| `REFLEX_BACKEND_URL` | 必须 `https://…` |
| `ANDROID_KEYSTORE_BASE64` | `base64 -w0 release.keystore` |
| `ANDROID_KEYSTORE_PASSWORD` | keystore 密码 |
| `ANDROID_KEY_ALIAS` | 别名 |
| `ANDROID_KEY_PASSWORD` | 密钥密码 |

Actions → **Android Release AAB** → Run workflow → 下载 `app-release-production`。

本地等价命令见 [publishing.md](publishing.md)。

## 可选：App 图标

`rxconfig.py`：

```python
CapacitorPlugin(
    backend_url="http://192.168.1.56:8001",
    icon="assets/icon.png",  # PNG，sync 后复制到 Android mipmap
)
```

需已 `reflex-capacitor init` 生成 `android/`。
