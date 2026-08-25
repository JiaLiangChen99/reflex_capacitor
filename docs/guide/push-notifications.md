# 远程推送（Push Notifications）

使用 `@capacitor/push-notifications` 注册设备并接收 FCM / APNs 推送（**可选**）。

> **可选能力，非默认依赖。** 上架 PyPI / 通用脚手架时**不要**把 `push-notifications` 放进默认 `plugins`；只有需要远程推送时再显式启用。本仓库 demo 为了演示才挂了 `PHASE5_PLUGIN_IDS`。配置分层见 [configuration.md](configuration.md)。

> **与本地通知的区别**：`mobile.notify()` 是 App 内触发的**本地通知**；远程推送由服务端经 Firebase（Android）或 APNs（iOS）下发。App 在线时也可用 WebSocket + `mobile.notify()`，不必强制接 FCM。

## 启用插件

在 `rxconfig.py` 的 `CapacitorPlugin(plugins=…)` 中加入 `push-notifications`：

```python
from reflex_capacitor.bridge.plugins import ALL_PLUGIN_IDS, PHASE5_PLUGIN_IDS

CapacitorPlugin(
    # 推荐默认：ALL_PLUGIN_IDS；需要远程推送再加 PHASE5
    plugins=ALL_PLUGIN_IDS + PHASE5_PLUGIN_IDS,
    ...
)
```

然后：

```bash
reflex-capacitor sync
```

`sync` 会安装 `@capacitor/push-notifications`、拷贝 vendor JS，并在 Android 13+ 写入 `POST_NOTIFICATIONS`（与 local-notifications 相同）。

## Reflex API

```python
from reflex_capacitor import mobile

# 请求权限并注册（结果通过 poll_native_events 或 callback 获取）
mobile.push_register(callback=State.on_push_register)

# 启动时监听推送相关原生事件
mobile.setup_native_listeners(back_button="emit")
mobile.poll_native_events(State.on_native_events)
```

### 原生事件类型

| type | detail | 含义 |
|------|--------|------|
| `pushRegistration` | `{ "value": "<device-token>" }` | 注册成功，token 发往后端 |
| `pushRegistrationError` | `{ "error": "…" }` | 注册失败 |
| `pushNotificationReceived` | `{ "id", "title", "body", "data" }` | 前台收到推送 |
| `pushNotificationActionPerformed` | `{ "actionId", "notification" }` | 用户点击通知 |

将 `pushRegistration.value` 保存到你的 Reflex 后端，用于 FCM / APNs 定向推送。

## Android（FCM）

1. 在 [Firebase Console](https://console.firebase.google.com/) 创建项目并添加 Android App（包名 = `CapacitorPlugin.app_id`）。
2. 下载 `google-services.json` 放到  
   `capacitor/android/app/google-services.json`。
3. 在 `capacitor/android/build.gradle` / `app/build.gradle` 按 [Capacitor 推送文档](https://capacitorjs.com/docs/apis/push-notifications) 应用 Google Services 插件。
4. 真机或带 Google Play 服务的模拟器上测试；无 GMS 的设备无法完成 FCM 注册。

`mobile.push_register()` 成功后，在 `pushRegistration` 事件里拿到 token，由后端调用 FCM HTTP v1 API 发推送。

## iOS（APNs）

1. Apple Developer 启用 Push Notifications capability。
2. 在 Xcode 打开 `ios/App`，Signing & Capabilities → **+ Push Notifications**。
3. 配置 APNs 密钥或证书，并在后端使用 APNs 发送。
4. 真机测试（模拟器不支持远程推送注册）。

## 权限

| 平台 | 权限 / 配置 |
|------|-------------|
| Android 13+ | `POST_NOTIFICATIONS`（运行时请求，`push_register` 内处理） |
| iOS | 系统推送授权弹窗 |
| 浏览器 | 不支持 Capacitor 远程推送；`push_register` 返回 `plugin_missing` 或 no-op |

详见 [permissions.md](permissions.md)。

## 调试提示

- 注册失败：检查 `google-services.json`、包名、Gradle 插件。
- 收不到推送：确认 token 已上传后端、App 未被系统省电策略杀死、通知渠道（Android）已创建。
- 点击通知无反应：在 `pushNotificationActionPerformed` 里解析 `notification.data` 并更新 State（类似深链处理）。
- Bridge 诊断：`mobile.diagnostics()` 的 `pluginsLoaded` 应含 `PushNotifications`。

## 限制

- 本包**不包含** FCM / APNs 服务端实现；仅提供客户端注册与事件桥。
- CI debug APK 未配置 Firebase 时，demo「注册推送」可能只走到权限步骤或 registrationError。
- 推送点击深链与 [deep-linking.md](deep-linking.md) 可组合：在 `data` 里带 URL，由 Reflex 解析。

## 相关

- [configuration.md](configuration.md) · [deep-linking.md](deep-linking.md) · [permissions.md](permissions.md)
- [plan.md](../design/plan.md) · [README.md](../README.md)
