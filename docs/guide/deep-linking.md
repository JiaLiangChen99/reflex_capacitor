# 深链（Deep Linking）

> 最后更新：2026-08-25 · 总索引 [README.md](../README.md)

从外部 URL 打开 App，并把链接交给 Reflex State 处理。

## 工作原理

1. 用户在浏览器 / 短信 / 其他 App 点击自定义 scheme 或 App Link。
2. Capacitor `@capacitor/app` 触发 `appUrlOpen`。
3. `reflex-capacitor` bridge 将事件写入原生事件队列。
4. Reflex 通过 `mobile.poll_native_events(callback)` 取出并路由。

Bridge 在 `setup_native_listeners` 时注册 `appUrlOpen`；本文说明原生侧 URL scheme / App Links 配置与 demo 展示。

## Reflex 侧用法

```python
import reflex as rx
from reflex_capacitor import mobile

class State(rx.State):
    last_deep_link: str = ""

    @rx.event
    def on_app_load(self):
        return [
            mobile.setup_native_listeners(back_button="emit"),
            mobile.poll_native_events(State.on_native_events),
        ]

    @rx.event
    def on_native_events(self, result):
        if not result or not isinstance(result, dict):
            return
        for ev in result.get("events") or []:
            if ev.get("type") == "appUrlOpen":
                url = (ev.get("detail") or {}).get("url") or ""
                self.last_deep_link = url
                # 在此解析 path/query，切换 tab 或跳转 State
```

事件形状：

```json
{
  "ts": "2026-08-24T12:00:00.000Z",
  "type": "appUrlOpen",
  "detail": { "url": "shell://open/home?ref=share" }
}
```

建议 App 启动时调用一次 `poll_native_events`，并在 `on_app_load` 注册 `setup_native_listeners`。

## Android 配置

在 `capacitor/android/app/src/main/AndroidManifest.xml` 的 `<activity android:name=".MainActivity">` 内添加 intent-filter（示例 scheme `shell`，与 `app_id` 无关，可自定）：

```xml
<intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="shell" android:host="open" />
</intent-filter>
```

测试（adb + 已安装 debug 包）：

```bash
adb shell am start -W -a android.intent.action.VIEW \
  -d "shell://open/home?from=adb" \
  com.example.yourapp
```

将 `com.example.yourapp` 换成 `rxconfig` 里 `CapacitorPlugin(app_id=…)` 的值。

### App Links（HTTPS，可选）

若要用 `https://your.domain/path` 打开 App，需：

- 域名 `assetlinks.json`
- Manifest 里 `android:autoVerify="true"` 的 https intent-filter

详见 [Android App Links 官方文档](https://developer.android.com/training/app-links)。本包暂不自动生成 App Links 片段。

## iOS 配置

在 Xcode 打开 `ios/App/App/Info.plist`，增加 URL Types（示例）：

```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLName</key>
    <string>dev.reflex.capacitor.demo</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>shell</string>
    </array>
  </dict>
</array>
```

模拟器测试：

```bash
xcrun simctl openurl booted "shell://open/home?from=sim"
```

## 与 Universal Links / App Links 的关系

| 方式 | URL 示例 | 配置复杂度 |
|------|----------|------------|
| Custom scheme | `shell://open/...` | 低，适合 demo / 内部跳转 |
| App Link / Universal Link | `https://example.com/app/...` | 高，需域名验证，适合生产分享 |

两种最终都通过 `appUrlOpen` 进入同一 Reflex 事件流。

## 限制

- Web 浏览器里 `reflex run` 不会收到 `appUrlOpen`（非 Capacitor 壳）。
- 深链不会自动改 Reflex 路由；需在 `on_native_events` 里解析 URL 并更新 State。
- 当前**不会**自动写入 Manifest / Info.plist 的 URL scheme（见 [plan.md](../design/plan.md)）；改原生工程后需重新 `reflex-capacitor sync`。

## 相关

- [dev-reload.md](dev-reload.md) · [02-native-bridge.md](02-native-bridge.md) · [README.md](../README.md)
