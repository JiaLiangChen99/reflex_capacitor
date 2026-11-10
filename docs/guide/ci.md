# CI：Android APK · iOS Simulator 冒烟

> 最后更新：2026-11-10 · 本机构建见 [android-build.md](android-build.md) · 总索引 [README.md](../README.md)

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

## iOS Simulator 编译冒烟（仅手动）

Workflow **iOS Simulator smoke**（**仅** `workflow_dispatch`，不在 push/PR 上运行）在 GitHub 托管 **macOS** runner 上验证：

1. 安装本仓库 Python 包与 Node 依赖  
2. `reflex-capacitor init --platform ios` + `sync`  
3. 对 **Simulator** 执行 `xcodebuild` 编译（`CODE_SIGNING_ALLOWED=NO`）

**触发：** Actions → **iOS Simulator smoke** → Run workflow。

**后端 URL：** 使用环境变量 `REFLEX_CAPACITOR_DEV_BACKEND_URL=https://api.example.com`（占位 HTTPS，与 Android CI 一样不在 workflow 里写死个人局域网 IP）。仓库内 `rxconfig.py` 的 LAN 地址会被覆盖。

### 覆盖范围 / 不覆盖

| 会验证 | 不会验证 |
|--------|----------|
| CLI 在 macOS 上 scaffold iOS 工程 | 真机安装、模拟器上启动 App |
| `reflex export` → `cap sync` → CocoaPods（如有） | Apple Developer 证书、描述文件 |
| 无签名条件下 Simulator **编译** | `reflex-capacitor build ios` / `npx cap build ios`（需要签名与导出） |
| baked env 含 `wss://…/_event`、bridge 注入 | TestFlight / App Store Archive |

本地若在 Mac 上需要可安装包，请用 Xcode 或配置签名后执行 `reflex-capacitor build ios`，见 [publishing.md](publishing.md)。

## 可选：App 图标

`rxconfig.py`：

```python
CapacitorPlugin(
    backend_url="http://192.168.1.56:8001",
    icon="assets/icon.png",  # PNG，sync 后复制到 Android mipmap
)
```

需已 `reflex-capacitor init` 生成 `android/`。

## 相关

- [publishing.md](publishing.md) · [android-build.md](android-build.md) · [configuration.md](configuration.md) · [README.md](../README.md)
