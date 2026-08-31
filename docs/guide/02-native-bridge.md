# 原生桥接：mobile.py 与 Capacitor 插件

> 最后更新：2026-08-25  
> **用法 + 能力表**（本文）· 打包注入原理 → [packaging.md](../design/packaging.md) · 权限 → [permissions.md](permissions.md) · 配置分层 → [configuration.md](configuration.md)

## 1. 先澄清：不是「Reflex UI 组件」

`reflex-desktop` 的系统通知 **不是** 新写一个 `rx.Notification` 视觉组件，而是：

```python
# desktop.py 模式
rx.button("notify", on_click=desktop.notify("Title", "Body"))
# → 返回 EventSpec
# → 浏览器/WebView 执行 JS
# → window.__TAURI__.… / invoke('reflex_desktop_notify', …)
```

Capacitor 侧同样采用：

```python
from reflex_capacitor import mobile

rx.button("通知", on_click=mobile.notify("标题", "正文"))
rx.button("分享", on_click=mobile.share(title="…", text="…", url="…"))
rx.button("震动", on_click=mobile.haptics_impact())
```

**原则**：Python 只生成 `rx.call_script`；真正干活的是壳里的 Capacitor 插件。  
可选后续再做「带 UI 的封装组件」（如带权限引导的设置页），但 **MVP 只做事件桥**，与 desktop 对齐。

---

## 2. JS 稳定面：`window.__REFLEX_CAPACITOR__`

### 2.1 为什么不能直接 `import { LocalNotifications } from '@capacitor/...'`

Reflex `export` 产出的是静态 HTML/JS，**不会**自动把 Capacitor npm 包装进 bundle。  
若只在原生侧 `npm i @capacitor/local-notifications`，Web 层仍可能没有可调用的 JS 绑定。

### 2.2 推荐方案

在拷贝到 `www/` 后注入：

1. Capacitor 运行时（`cap sync` 已处理原生侧）。
2. 本包自带的 `bridge.js`（路径：`www/assets/reflex-capacitor/bridge.js`），挂载：

```js
// 伪代码：稳定 API，屏蔽各插件版本差异
window.__REFLEX_CAPACITOR__ = {
  async notify({ title, body }) { /* LocalNotifications */ },
  async clipboardWrite(text) { … },
  async clipboardRead() { … },
  async share({ title, text, url }) { … },
  async hapticsImpact(style) { … },
  async toast(text) { … },
  async takePhoto(options) { … },
  // …
  isNative: () => Cap.isNativePlatform(),
  platform: () => Cap.getPlatform(),
};
```

`mobile.*`（`bridge/api.py`）**只**调用 `__REFLEX_CAPACITOR__`，不对齐各插件原始方法名。

注入方式（`post_build` / `sync`）：

- 复制 `bridge.js` → `www/assets/reflex-capacitor/`
- 在 `index.html` 插入带 marker 的 `<script src="…/bridge.js">`（幂等）
- `finalize_bridge`：从 `node_modules` 拷 vendor、补 Manifest / Info.plist

详见 [packaging.md](../design/packaging.md)。

### 2.3 浏览器降级

非 Cap 环境（纯 Chrome 调试）：

- `notify` → `console.warn` 或 `Notification` Web API（若可用）
- `haptics` → no-op
- `share` → `navigator.share` 或 no-op  
保证 `reflex run` 不因 `mobile.*` 炸掉。

---

## 3. 与 desktop.py 的能力对照

| desktop.py | 移动端意义 | Capacitor 插件 | mobile.py 建议 API | 优先级 |
|------------|------------|----------------|-------------------|--------|
| `notify` | 本地通知 | `@capacitor/local-notifications` | `notify(title, body="")` | **P0** |
| `clipboard_write/read` | 剪贴板 | `@capacitor/clipboard` | `clipboard_write` / `clipboard_read(callback)` | **P0** |
| `open_file` / `save_file` | 选文件 | `@capacitor/filesystem` + File Picker / 自定义 | `pick_file` / `save`（路径语义不同） | P1 |
| `invoke` | 自定义原生命令 | 自定义 Cap Plugin | `invoke(name, args, callback=)` | P1 |
| `minimize` / `maximize` / `close` / `start_dragging` / `set_title` / `set_fullscreen` | 桌面窗口 | — | **不提供**（或 `app.exitApp()` 仅 Android） | — |

桌面没有、移动端 **应新增** 的能力：

| 能力 | 插件 | mobile API 草案 | 优先级 |
|------|------|-----------------|--------|
| 状态栏 | `@capacitor/status-bar` | `status_bar_set_style` / `hide` / `show` | P0 |
| 启动屏 | `@capacitor/splash-screen` | `splash_hide` | P0 |
| App 生命周期 | `@capacitor/app` | `app_exit`；监听见 §5 | P0 |
| 震动反馈 | `@capacitor/haptics` | `haptics_impact` / `haptics_notification` | P0 |
| 系统分享 | `@capacitor/share` | `share(title=, text=, url=, dialog_title=)` | P0 |
| Toast | `@capacitor/toast` | `toast(text, duration=)` | P0 |
| 设备信息 | `@capacitor/device` | `device_info(callback)` | P0 |
| 网络状态 | `@capacitor/network` | `network_status(callback)` | P0 |
| 本地 KV | `@capacitor/preferences` | `pref_set` / `pref_get(callback)` | P1 |
| 文件系统 | `@capacitor/filesystem` | `fs_read` / `fs_write`（沙箱路径） | P1 |
| 相机 | `@capacitor/camera` | `take_photo(callback, …)` / `pick_images(callback)` | P1 |
| 定位 | `@capacitor/geolocation` | `get_current_position(callback)` | P1 |
| 键盘 | `@capacitor/keyboard` | `keyboard_show/hide`；事件见 §5 | P1 |
| 推送 | `@capacitor/push-notifications` | `push_register` + 事件 | **可选**（PHASE5） |
| 生物识别 | community / `@capawesome/...` | `biometric_verify(callback)` | 未做 |
| 条码扫描 | community | `scan_barcode(callback)` | 未做 |
| 应用内浏览器 | `@capacitor/browser` | `browser_open(url)` | P1（EXTENDED） |
| 录音 / 回放 | 内置 `bridge.js`（MediaRecorder） | `start_recording` / `stop_recording` / `play_recording` | P1（EXTENDED，builtin） |
| 系统播报 TTS | 内置 `bridge.js`（`speechSynthesis`） | `speak` / `stop_speak` | 随 bridge 提供；走系统 TTS，适合播报 LLM 文本 |

> **「组件」**：Capacitor 官方几乎都是 **命令式 Plugin API**，不是 React Native 那种 `<Camera />` 组件。Google Maps 等少数带 Web Component；MVP **不包地图组件**，需要时再单独立项。

---

## 4. `mobile.py` API 形状（对标 desktop.py）

### 4.1 无返回值（fire-and-forget）

```python
def notify(title: str, body: str = "") -> rx.event.EventSpec:
    payload = json.dumps({"title": title, "body": body})
    return rx.call_script(
        f"window.__REFLEX_CAPACITOR__.notify({payload})"
    )
```

实现要点（对标 `desktop.notify`）：

- 先 `checkPermissions` / `requestPermissions`
- 未授权则 no-op 并 `console.error`（避免静默失败无日志）
- 调度：`schedule` 立即本地通知（或 `LocalNotifications.schedule`）

### 4.2 有返回值（callback）

与 `clipboard_read` / `open_file` 相同模式：

```python
def take_photo(callback, *, quality: int = 90) -> rx.event.EventSpec:
    return rx.call_script(
        f"window.__REFLEX_CAPACITOR__.takePhoto({json.dumps({'quality': quality})})",
        callback=callback,
    )

# 用法
class State(rx.State):
    photo_data_url: str = ""

    @rx.event
    def on_photo(self, result):
        # result 来自 bridge：{ "dataUrl": "..." } 或 null
        if result:
            self.photo_data_url = result["dataUrl"]
```

**注意**：remote 模式下后端在云上——`open()` 本地路径 **不能** 像 desktop embedded 那样直接读用户磁盘。  
相机/文件应返回 **base64 / dataUrl / 上传后的 URL**，由 State 决定是否 `upload` 到服务器。文档必须写清这一差异。

### 4.3 `invoke`（扩展缝）

```python
def invoke(command: str, args: Mapping | None = None, *, callback=None) -> EventSpec:
    # 调用自定义 Capacitor 插件或 bridge 上挂的扩展方法
```

便于用户在 `android/` / `ios/` 加自定义 Plugin，而不改 `mobile.py`。

### 4.4 类型桩

提供 `bridge/api.pyi`（经 `mobile` 导出），便于编辑器补全。

---

## 5. 原生 → Reflex 的反向事件

移动端常见：

- 物理返回键（Android）
- App 进入后台 / 前台
- 键盘显隐
- 深链 `appUrlOpen`

实现：

1. App 启动时调用 `mobile.setup_native_listeners(back_button="emit")` 注册 Capacitor 监听。
2. 用 `mobile.poll_native_events(callback)` 取出事件队列（`[{ts, type, detail}, …]`）。
3. `back_button`：`emit`（默认，入队）| `exit` | `history`。

详见 [dev-reload.md](dev-reload.md)。深链 → [deep-linking.md](deep-linking.md)；推送（可选）→ [push-notifications.md](push-notifications.md)。

---

## 6. 权限与清单

每个启用的插件，`finalize_bridge` 会尽可能写入 Manifest / Info.plist。完整表 → [permissions.md](permissions.md)。  
`CapacitorPlugin(plugins=(...))` 决定 npm 包 **以及** 权限片段（幂等）。分层常量 → [configuration.md](configuration.md)。

---

## 7. 推荐默认插件集

| 层级 | 常量 | 典型内容 |
|------|------|----------|
| 核心 | `CORE_PLUGIN_IDS` | app、splash、status-bar、notify、toast、haptics、clipboard、share、device、network |
| 扩展 | `EXTENDED_PLUGIN_IDS` | camera、geolocation、filesystem、preferences、keyboard、browser、voice-recorder |
| 推荐默认 | `ALL_PLUGIN_IDS` | CORE + EXTENDED（**不含**推送） |
| 可选 | `PHASE5_PLUGIN_IDS` | `push-notifications`（需自备 FCM/APNs） |

---

## 8. Demo 应演示的能力

仓库 `demo/` 的「原生」Tab 覆盖：

- `mobile.notify` / `toast` / `haptics_*` / `share` / clipboard
- `device_info` / `network_status` / `platform_info`
- `take_photo` / 定位 / 偏好 / 反向事件（返回键、深链展示）
- 可选：推送注册（需 Firebase）

---

## 9. 图片编辑器（可选）

本机裁剪/压缩，默认不上传云端：

```python
mobile.capture_and_edit(State.on_edited, source="camera")
```

详见 demo「原生」Tab；推荐 `return_data_url=False` + 沙箱路径，避免大图经 WebSocket 回传后端。

---

## 相关

- [configuration.md](configuration.md) · [packaging.md](../design/packaging.md) · [permissions.md](permissions.md) · [docs/README.md](../README.md)
