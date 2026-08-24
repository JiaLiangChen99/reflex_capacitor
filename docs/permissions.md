# Capacitor 插件权限说明

Phase 2 默认插件及其 Android / iOS 权限。Bridge 在调用时按需请求运行时权限（例如通知）。

## 目录结构

Python ↔ Capacitor 桥接代码位于 `src/reflex_capacitor/bridge/`：

| 模块 | 职责 |
|------|------|
| `api.py` | Python `mobile.*` API（`rx.call_script`） |
| `assets/bridge.js` | `window.__REFLEX_CAPACITOR__` 实现 |
| `inject.py` | 复制 bridge.js、注入 `index.html` |
| `plugins.py` | npm 包映射、vendor 拷贝、Manifest 补丁 |

## 默认插件（P0）

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

## 自定义插件

在 `rxconfig.py` 的 `CapacitorPlugin(plugins=(...))` 中追加 short id（见 `bridge/plugins.py` 的 `PLUGIN_PACKAGES`），然后：

```bash
reflex-capacitor sync
```

`sync` 会更新 `package.json`、安装 npm 依赖、拷贝 vendor JS，并 `cap sync` 原生工程。

## 真机调试提示

- **通知**：Android 13+ 需用户授予通知权限；首次 `mobile.notify()` 会触发 `requestPermissions`。
- **LAN HTTP 后端**：见 [ci.md](ci.md)（cleartext + `androidScheme: http`）。
