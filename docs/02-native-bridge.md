# 原生桥接设计：mobile.py 与 Capacitor 插件

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
2. 本包自带的 `reflex-capacitor-bridge.js`，挂载：

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

`mobile.py` **只**调用 `__REFLEX_CAPACITOR__`，不对齐各插件原始方法名（类似 desktop 统一封装 `__TAURI__`）。

注入方式（`post_build` / `sync`）：

- 复制 `reflex-capacitor-bridge.js` → `www/assets/`
- 在 `index.html` 的 `</body>` 前插入 `<script src="./assets/reflex-capacitor-bridge.js"></script>`（幂等：有标记则跳过）

Bridge 内部用 `Capacitor.Plugins` 或动态 `registerPlugin`（视 Cap 大版本而定，实现时以当时官方文档为准）。

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
| 推送 | `@capacitor/push-notifications` | `push_register` + 事件 | P2 |
| 生物识别 | community / `@capawesome/...` | `biometric_verify(callback)` | P2 |
| 条码扫描 | community | `scan_barcode(callback)` | P2 |
| 应用内浏览器 | `@capacitor/browser` | `browser_open(url)` | P2 |

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

提供 `mobile.pyi`，与 desktop 一样让编辑器补全。

---

## 5. 原生 → Reflex 的反向事件（desktop 弱、移动端强）

桌面桥几乎是 **Python→原生单向**。移动端常见：

- 物理返回键（Android）
- App 进入后台 / 前台
- 推送点击
- 键盘显隐
- 深链 `appUrlOpen`

建议二期机制：

1. Bridge 监听 Cap 事件，写入 `window` 或调用一小段约定脚本。
2. 或通过 `rx.call_script` 注册：`mobile.on_app_state(State.handle_state)` 在 `on_mount` 挂监听，内部用 Capacitor listener + 自定义 DOM event，再触发 Reflex。

MVP 可先 **文档列出、API 占位**；P0 只做 Python→原生命令。

---

## 6. 权限与清单（开发必做）

每个启用的插件，脚手架/`post_build` 应尽可能写入：

| 平台 | 动作 |
|------|------|
| iOS | `Info.plist` 用途字符串（相机、定位、麦克风、相册…） |
| Android | `AndroidManifest.xml` permissions；部分需 runtime 请求 |
| 两端 | 首次调用前 `requestPermissions`（bridge 内统一做） |

`CapacitorPlugin(plugins=(...))` 决定安装哪些 npm 包 **以及** 是否生成对应权限片段（可用托管区注释标记，幂等更新）。

---

## 7. 推荐默认插件集（开箱）

与「大部分联网 App」匹配的默认 `plugins`：

```text
app, splash-screen, status-bar,
local-notifications, toast, haptics,
clipboard, share,
device, network,
keyboard
```

按需开启（增大包体 / 审核敏感）：

```text
camera, geolocation, filesystem, preferences,
push-notifications
```

---

## 8. Example 应用应演示的能力（对标 example/counter）

在 `example/` 中做一页 **Native**，按钮调用：

- `mobile.notify`
- `mobile.toast` / `mobile.haptics_impact`
- `mobile.share`
- `mobile.clipboard_write` + `clipboard_read`
- `mobile.status_bar_set_style`
- `mobile.device_info` / `network_status`（callback 显示在 State）
- （P1）`mobile.take_photo`

并注明：后端可为任意已部署 Reflex URL；example 可用 remote mock 或官方 demo 后端。
