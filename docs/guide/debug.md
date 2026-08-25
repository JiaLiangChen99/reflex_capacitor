# Bridge 调试指南

> 最后更新：2026-08-25 · 总索引 [README.md](../README.md)

原生桥自带 **客户端日志环** 与 **后端 Python 日志**，方便真机 APK 测试。  
上手 → [00-getting-started.md](00-getting-started.md) · 本机环境 → [android-build.md](android-build.md)

## App 内查看（推荐）

1. 打开 App → **原生** Tab
2. 进入时会自动拉取 **诊断** 与 **客户端日志**
3. 点原生按钮（通知 / Toast / 分享等）后，日志会自动刷新（void 操作）或出现在 **回调结果**（带 callback 的操作）
4. 面板说明：
   - **诊断**：`isNative`、`platform`、已加载 / 缺失的 Capacitor 插件、`logCount`
   - **客户端日志**：`bridge.js` 环缓冲（最近 100 条），含每次调用的 args / result / error
   - **服务端日志**：Reflex 后端收到的 callback / 诊断摘要（需后端在线）

## 后端终端查看

Demo 已启用：

```python
logging.getLogger("reflex_capacitor.bridge").setLevel(logging.DEBUG)
```

启动后端：

```powershell
reflex run --env prod --backend-only --backend-host 0.0.0.0 --backend-port 8001
```

终端会出现类似：

```
INFO reflex_capacitor.bridge: [12:34:56] (server) notify args={"title": "Shell"}
INFO reflex_capacitor.bridge: [12:34:57] (client) callback result={"value": "..."}
```

在自己的 App 里可同样配置 logger，或：

```python
from reflex_capacitor.bridge import log_bridge

@rx.event
def on_result(self, data):
    self._append_server_log(log_bridge("deviceInfo", result=data, source="client"))
```

## Python API

```python
from reflex_capacitor import mobile

# 诊断与日志（需在事件 handler 里调用）
mobile.diagnostics(State.on_diagnostics)
mobile.bridge_logs(50, State.on_client_logs)
mobile.clear_logs()
```

## Chrome 远程调试（可选）

Android 真机 USB 调试时，Chrome 打开 `chrome://inspect` 可查看 WebView `console`；
`bridge.js` 同时会 `console.log` 每条 `[reflex-capacitor]` 记录。

## 常见问题

| 现象 | 排查 |
|------|------|
| 诊断 `bridge_not_loaded` | 未执行 `reflex-capacitor sync`，或 `index.html` 未注入 bridge |
| `pluginsMissing` 非空 | `npm install` / `finalize_bridge` 未跑，vendor JS 缺失 |
| 客户端有日志、服务端无 | 正常：void 调用（notify/toast）只在 WebView 执行；带 callback 的才会回后端 |
| `isNative: false` | 在浏览器打开，非 Capacitor 壳 |
| WebSocket / 连不上后端 | 后端 `0.0.0.0`、同 Wi‑Fi、HTTP 需 cleartext；见 [android-build.md](android-build.md) |
| Gradle / 缺 SDK | `reflex-capacitor check --android` |

## 相关

- [cli.md](cli.md) · [02-native-bridge.md](02-native-bridge.md) · [../design/testing.md](../design/testing.md) · [README.md](../README.md)
