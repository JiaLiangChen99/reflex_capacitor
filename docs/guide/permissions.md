# Capacitor 插件权限说明

> 最后更新：2026-08-25 · 插件分层见 [configuration.md](configuration.md) · 总索引 [README.md](../README.md)

默认 / 扩展插件及其 Android / iOS 权限。Bridge 在调用时按需请求运行时权限（例如通知）。

## 目录结构

Python ↔ Capacitor 桥接代码位于 `src/reflex_capacitor/bridge/`：

| 模块 | 职责 |
|------|------|
| `api.py` | Python `mobile.*` API（`rx.call_script`） |
| `assets/bridge.js` | `window.__REFLEX_CAPACITOR__` 实现 |
| `inject.py` | 复制 bridge.js、注入 `index.html` |
| `plugins.py` | npm 包映射、vendor 拷贝、Manifest 补丁 |

## 默认插件（核心）

| 插件 | Android | iOS | 备注 |
|------|---------|-----|------|
| local-notifications | `POST_NOTIFICATIONS`（API 33+） | 用户授权弹窗 | `finalize_bridge` 自动写入 Manifest |
| clipboard | 无额外权限 | 无 | |
| haptics | `VIBRATE` | 无 | 系统自带 |
| share | 无 | 无 | 系统分享表 |
| status-bar | 无 | 无 | |
| app | 无 | 无 | |
| splash-screen | 无 | 无 | |
| toast | 无 | 无 | |
| device | 无 | 无 | 只读设备信息 |
| network | `ACCESS_NETWORK_STATE` | 无 | Cap sync 通常已包含 |
| preferences | 无 | 无 | 本地 KV |
| camera | `CAMERA`, `READ_MEDIA_IMAGES`, `READ/WRITE_EXTERNAL_STORAGE` | 相机/相册用途说明 | `saveToGallery: true` 时写入系统相册 |
| geolocation | `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION` | 定位用途说明 | 运行时请求 |
| keyboard | 无 | 无 | |
| browser | 无 | 无 | 应用内浏览器 |
| filesystem | 无（沙箱内） | 无 | 仅 app 沙箱目录 |
| text-to-speech | Android 11+ 需 `TTS_SERVICE` queries；`sync` 会注入本地 `AudioFocusPlugin` | 系统 TTS 引擎；播报时抢音频焦点 | `@capacitor-community/text-to-speech`；`mobile.speak(..., audio_focus=)` |

## 默认插件

`CapacitorPlugin` 默认使用 `ALL_PLUGIN_IDS`（CORE + EXTENDED，见 `bridge/plugins.py`）。

若只要核心插件，显式传 `plugins=CORE_PLUGIN_IDS` 或自定义 tuple。

## 可选插件（推送等）

demo 额外启用 `PHASE5_PLUGIN_IDS`（当前含 `push-notifications`）：

```python
plugins=ALL_PLUGIN_IDS + PHASE5_PLUGIN_IDS
```

| 插件 | Android | iOS | 备注 |
|------|---------|-----|------|
| push-notifications | `POST_NOTIFICATIONS`（API 33+） | Push capability + 用户授权 | 需 Firebase / APNs；见 [push-notifications.md](push-notifications.md) |

深链（`appUrlOpen`）不额外声明权限；URL scheme 见 [deep-linking.md](deep-linking.md)。

`sync` / `finalize_bridge` 会在 **`ios/App/App/Info.plist` 存在时** 自动写入相机/定位/推送等用途说明（幂等）。

## 自定义插件

在 `rxconfig.py` 的 `CapacitorPlugin(plugins=(...))` 中追加 short id（见 `bridge/plugins.py` 的 `CAPACITOR_PLUGIN_PACKAGES`），然后：

```bash
reflex-capacitor sync
```

`sync` 会更新 `package.json`、安装 npm 依赖、拷贝 vendor JS，并 `cap sync` 原生工程。

## 真机调试提示

- **通知**：Android 13+ 需用户授予通知权限；首次 `mobile.notify()` 会触发 `requestPermissions`。
- **LAN HTTP 后端**：见 [configuration.md](configuration.md) / [ci.md](ci.md)（cleartext + `androidScheme: http`）。

## 相关

- [configuration.md](configuration.md) · [02-native-bridge.md](02-native-bridge.md) · [push-notifications.md](push-notifications.md)
