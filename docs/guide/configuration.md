# 配置指南

> 最后更新：2026-08-25

唯一配置源：`rxconfig.py` 里的 `CapacitorPlugin`。每次 `sync` / `export` 会幂等重写「托管区」；托管区外的手改会保留。

---

## CapacitorPlugin 常用字段

| 字段 | 默认 | 说明 |
|------|------|------|
| `backend_url` | `None` | 远端 Reflex API；也可用环境变量覆盖 |
| `app_id` | 由 app 名推导 | 反向域名，如 `com.example.myapp` |
| `app_name` | Reflex `app_name` | 桌面显示名 |
| `capacitor_dir` | `"capacitor"` | Cap 工程目录 |
| `web_dir` | `"www"` | 静态资源目录名（相对 `capacitor_dir`） |
| `plugins` | **`ALL_PLUGIN_IDS`** | 短 id 元组（CORE + EXTENDED）；推送仍需另加 `PHASE5_PLUGIN_IDS` |
| `icon` | `None` | 可选 PNG，sync 时拷到 Android mipmap |

```python
from reflex_capacitor import CapacitorPlugin

CapacitorPlugin(
    backend_url="https://api.example.com",
    app_id="com.example.myapp",
    app_name="My App",
    # plugins 默认已是 ALL_PLUGIN_IDS；要缩小体积再传 CORE_PLUGIN_IDS
)
```

---

## 插件分层

| 常量 | 内容 | 何时用 |
|------|------|--------|
| `ALL_PLUGIN_IDS` | CORE + EXTENDED | **默认**（相机/定位/TTS/录音等，不含推送） |
| `CORE_PLUGIN_IDS` | 通知、剪贴板、分享、状态栏、设备、网络… | 想瘦身时显式传入 |
| `EXTENDED_PLUGIN_IDS` | 相机、定位、文件系统、键盘、browser、录音、TTS… | 一般不必单独用 |
| `PHASE5_PLUGIN_IDS` | 当前含 `push-notifications` | **显式**需要远程推送时再加 |

```python
from reflex_capacitor.bridge.plugins import ALL_PLUGIN_IDS, CORE_PLUGIN_IDS, PHASE5_PLUGIN_IDS

# 默认即可，不必写 plugins=

# 瘦身
plugins=CORE_PLUGIN_IDS

# 需要远程推送时
plugins=ALL_PLUGIN_IDS + PHASE5_PLUGIN_IDS
```
推送需自备 Firebase / APNs；本包**不含**服务端实现 → [push-notifications.md](push-notifications.md)。

---

## backend_url 与网络安全

| 场景 | URL | 插件行为 |
|------|-----|----------|
| 局域网调试 | `http://192.168.x.x:8001` | 自动 `cleartext` + `androidScheme: http` + Manifest 明文 |
| 生产 / 上架 | `https://…` | 走 HTTPS / WSS；勿长期开 cleartext |
| 模拟器访本机 | `http://10.0.2.2:8000` | 同 HTTP 明文规则 |

另需：

```python
cors_allowed_origins=["*"]  # 或明确列出 capacitor://localhost、http://localhost 等
```

开发时可用环境变量覆盖烘焙地址：`REFLEX_CAPACITOR_DEV_BACKEND_URL`（见 [dev-reload.md](dev-reload.md)）。

**CORS / 生产安全**：WebView origin（`capacitor://localhost` 等）与 API 不同源；开发可用 `["*"]`，生产请收紧。LAN 改 HTTPS 后须重新 `sync`。keystore / FCM 密钥 / `google-services.json` **勿提交 git**（见 [install.md](install.md) §5）。

---

## 平台检测（iOS / Android）

Python 后端**无法**直接读当前是 iOS 还是 Android；在壳内用：

```python
mobile.platform_info(State.on_platform)  # callback → isAndroid / isIos / platform
```

| 环境 | 说明 |
|------|------|
| `reflex run` 浏览器 | `web`，bridge 降级不报错 |
| Android / iOS 壳 | 需 macOS 才能打 iOS 包 |

---

## 与 reflex-desktop 共存

同一仓库可同时挂 `DesktopPlugin` + `CapacitorPlugin`（目录分别为 `tauri/` 与 `capacitor/`）。业务层按平台分流 `desktop.*` / `mobile.*` 即可。

---

## 相关

- 命令 → [cli.md](cli.md)
- 权限清单 → [permissions.md](permissions.md)
- 架构 → [01-architecture.md](../design/01-architecture.md)
