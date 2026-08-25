# 快速上手

> 最后更新：2026-08-25  
> 平台：**Android**（Windows/Linux 可开发）；**iOS** 需 Mac。

最短路径：装好依赖 → 配 `backend_url` → `init` / `sync` → 真机或 CI 出包。细节见专题文档；总索引见 [README.md](../README.md)。

---

## 1. 安装与检查

```bash
pip install reflex-capacitor   # 或本仓库: pip install -e .
reflex-capacitor check --android
```

- 缺什么会逐条列出；**本 CLI 不代装** Node / JDK / Android SDK。
- 安装与 PyPI 发布说明 → [install.md](install.md)
- 仅同步前端：`check`（不必 `--android`）。
- 真机运行：`check --android --device`（要求 `adb`）。

环境说明 → [android-build.md](android-build.md) · 命令全集 → [cli.md](cli.md)

---

## 2. 最小配置

```python
import reflex as rx
from reflex_capacitor import CapacitorPlugin
from reflex_capacitor.bridge.plugins import ALL_PLUGIN_IDS

config = rx.Config(
    app_name="demo",
    cors_allowed_origins=["*"],  # 生产请收紧
    plugins=[
        CapacitorPlugin(
            backend_url="http://192.168.1.56:8001",  # 生产用 https://
            app_id="dev.reflex.myapp",
            app_name="My App",
            plugins=ALL_PLUGIN_IDS,  # 推送等见 configuration.md
        ),
    ],
)
```

| 环境 | `backend_url` |
|------|----------------|
| 局域网调试 | `http://<PC局域网IP>:端口`（自动 cleartext） |
| 生产 | `https://api.example.com` |

完整配置 → [configuration.md](configuration.md)

---

## 3. 首次出包

```bash
reflex-capacitor init --platform android
reflex-capacitor sync
reflex-capacitor run android          # 需设备/模拟器
# 或只打 APK：
reflex-capacitor build android --debug
```

下载慢时显式代理（默认**不用**代理）：

```bash
reflex-capacitor sync --proxy http://127.0.0.1:7890
```

无本机 SDK → [ci.md](ci.md)。后端需 `0.0.0.0`，手机与 PC 同网。

日常开发 → [dev-reload.md](dev-reload.md) · 调试 → [debug.md](debug.md)

---

## 4. 原生 API（摘录）

```python
from reflex_capacitor import mobile

mobile.notify("标题", "正文")
mobile.get_current_position(State.on_gps)
mobile.setup_native_listeners(back_button="emit")
mobile.poll_native_events(State.on_native_events)
```

完整表 → [02-native-bridge.md](02-native-bridge.md) · 权限 → [permissions.md](permissions.md)

---

## 5. 发布

```bash
reflex-capacitor build android              # release APK
reflex-capacitor build android --format aab
```

签名与上架 → [publishing.md](publishing.md)

---

## 6. 已知限制

- **仅 remote 后端**（设备上不跑 Python）
- **推送可选**（`PHASE5_PLUGIN_IDS`）→ [push-notifications.md](push-notifications.md)
- **iOS** 需 Mac；本仓库 CI 未跑 iOS
- 定位等机型差异 → [debug.md](debug.md)

变更记录 → [CHANGELOG.md](../../CHANGELOG.md) · 常见问题 → [faq.md](faq.md)
