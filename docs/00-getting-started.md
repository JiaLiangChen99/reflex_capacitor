# 快速上手（Phase 1–4 总览）

> 最后更新：2026-08-24  
> 适用平台：**Windows + Android 真机/模拟器**（iOS 需 Mac，见下文）

本文把各阶段文档串成一条可执行路径。细节见各专题文档。

---

## 1. 安装与配置

```bash
pip install -e .
reflex-capacitor doctor
reflex-capacitor doctor --android   # 本机要打 APK 时
```

`rxconfig.py` 最小示例：

```python
import reflex as rx
from reflex_capacitor import CapacitorPlugin
from reflex_capacitor.bridge.plugins import ALL_PLUGIN_IDS

config = rx.Config(
    app_name="demo",
    cors_allowed_origins=["*"],  # 生产环境请收紧
    plugins=[
        CapacitorPlugin(
            backend_url="http://192.168.1.56:8001",  # 生产改为 https://
            app_id="dev.reflex.myapp",
            app_name="My App",
            plugins=ALL_PLUGIN_IDS,
        ),
    ],
)
```

| 环境 | `backend_url` | 说明 |
|------|---------------|------|
| 局域网调试 | `http://<PC局域网IP>:8001` | 插件自动设 `cleartext` + `androidScheme: http` |
| 生产 / 上架 | `https://api.example.com` | 必须 HTTPS + WSS |

---

## 2. 首次打包（本地或 CI）

```bash
reflex-capacitor init --platform android
reflex-capacitor sync
reflex-capacitor run android          # 需设备/模拟器 + Android Studio SDK
```

**无 Android Studio 时**：用 GitHub Actions 打 debug APK → [ci.md](ci.md)

```bash
# 后端需监听 0.0.0.0，手机与 PC 同 Wi‑Fi
reflex run --env prod --backend-only --backend-host 0.0.0.0 --backend-port 8001
```

真机安装 APK 后，在 App「原生」Tab 测 P0/P1 能力；调试见 [debug.md](debug.md)。

---

## 3. 开发模式（有数据线 / 本机 SDK 时）

```bash
reflex-capacitor dev android              # 默认：打包 UI + 后端热跑
reflex-capacitor dev android --live-reload  # UI 也从 Vite 加载（需 LAN 可达前端端口）
```

详见 [dev-reload.md](dev-reload.md)。

---

## 4. 原生能力（Python API）

```python
from reflex_capacitor import mobile

# P0 — 通知、分享、剪贴板、设备信息…
mobile.notify("标题", "正文")

# P1 — 相机、定位、偏好、沙箱文件…
mobile.take_photo(State.on_photo)
mobile.get_current_position(State.on_gps)

# 反向事件 — 返回键、前后台、键盘
mobile.setup_native_listeners(back_button="emit")
mobile.poll_native_events(State.on_native_events)

# 本机图片编辑（不上云）
mobile.capture_and_edit(State.on_edited, source="camera")
```

完整 API 表：[02-native-bridge.md](02-native-bridge.md)  
权限说明：[permissions.md](permissions.md)  
内置编辑器：[image-editor.md](image-editor.md)

---

## 5. 发布（Phase 4）

```bash
# 配置 REFLEX_CAPACITOR_KEYSTORE_* 后
reflex-capacitor build android              # release APK
reflex-capacitor build android --format aab # Google Play
```

签名、Play 上架、CI release AAB：[publishing.md](publishing.md)

---

## 6. 平台说明

| 平台 | Windows 可开发 | 可真机测试 | 本仓库 CI |
|------|----------------|------------|-----------|
| Android | ✅ | ✅ | debug APK + 可选 release AAB |
| iOS | ❌（需 Mac） | ❌（需 Mac + Xcode） | 未配置 |

iOS 相关 CLI（`run ios` / `build ios`）在 Windows 上会直接报错；有 Mac 时再执行 `init --platform ios`。

---

## 7. 文档索引

| 文档 | 内容 |
|------|------|
| [04-roadmap.md](04-roadmap.md) | 各 Phase 完成情况 |
| [01-architecture.md](01-architecture.md) | 架构与数据流 |
| [02-native-bridge.md](02-native-bridge.md) | `mobile.*` API 设计 |
| [ci.md](ci.md) | GitHub Actions 打 APK / release AAB |
| [dev-reload.md](dev-reload.md) | `reflex-capacitor dev` |
| [publishing.md](publishing.md) | 签名与上架 |
| [debug.md](debug.md) | 真机调试 |
| [permissions.md](permissions.md) | 插件权限 |
| [image-editor.md](image-editor.md) | 内置图片编辑器 |
| [03-development-plan.md](03-development-plan.md) | 踩坑与决策记录 |

---

## 8. 已知限制 / 待优化

- **定位**：原生接口已接，部分机型仍可能超时（与 HTTP 后端无关）；见 [debug.md](debug.md)
- **远程推送**：未实现，需 FCM/APNs（按需）
- **iOS**：无 Mac 无法验证

变更记录：根目录 [CHANGELOG.md](../CHANGELOG.md)
