# 架构设计：对标 reflex-desktop

## 1. reflex-desktop 在做什么（必须先对齐）

Reflex 应用 = **静态前端 SPA** + **Python ASGI 后端**。

`reflex-desktop` 拆成三层：

| 层 | 模块 | 职责 |
|----|------|------|
| Reflex 插件 | `DesktopPlugin` | `update_env_json` 烘焙后端 URL；`post_build` 脚手架 + 拷贝 `dist/`；按 `rxconfig` 改写 Tauri 配置 |
| Python→原生桥 | `desktop.py` | `rx.call_script(...)` 调用 `window.__TAURI__.*`（通知、窗口、对话框、剪贴板、`invoke`） |
| CLI | `cli.py` | `dev` / `run` / `build` / `doctor`：驱动 `reflex export` + cargo / tauri-cli |

关键设计决策（应原样继承到 Capacitor）：

1. **`rxconfig` 是唯一配置源** — 每次 build 幂等重写「托管区域」，手改托管区外代码保留。
2. **后端地址写进 `env.json`** — 静态前端没有运行时协商端口的通道；`Endpoint.EVENT` 要改成 `ws://` / `wss://`。
3. **原生能力不是 Reflex 组件，是事件桥** — 通知等不是 `rx.notification()` UI 组件，而是 `on_click=desktop.notify(...)` 返回的 `EventSpec`。
4. **CORS** — WebView origin 与后端不同源时必须放行（桌面是 `tauri://localhost`；移动端是 `capacitor://localhost` / `http://localhost` 等）。
5. **dev ≠ 生产壳** — `dev` 指向热重载的 `reflex run`；`run`/`build` 用导出的静态前端。

桌面独有、**本项目刻意不做**：

- `backend="embedded"` / PyO3 / `runtime.py` / `bootstrap.py`
- 窗口控件（minimize / maximize / tray / start_dragging）
- Rust scaffold、capabilities、updater 签名链路

---

## 2. reflex-capacitor 目标架构

```text
┌─────────────────────────────────────────────────────────────┐
│ 开发者 Reflex 工程                                           │
│  rxconfig.py  →  plugins=[CapacitorPlugin(backend_url=...)] │
│  app/*.py     →  from reflex_capacitor import mobile        │
│                  on_click=mobile.notify("标题", "正文")       │
└───────────────────────────┬─────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
  CapacitorPlugin     mobile.py            CLI
  update_env_json     rx.call_script  reflex-capacitor
  post_build          → window.         init / sync /
  scaffold Cap        __REFLEX_CAP__     run / build /
                      或 Capacitor.*     doctor / open
         │                  │                  │
         └────────┬─────────┴────────┬─────────┘
                  ▼                  ▼
         <app>/capacitor/     云端 Reflex 后端
           www/  ← 静态前端      (api_url / wss)
           ios/  android/
           capacitor.config.*
           package.json (+ @capacitor/*)
```

**运行时（remote）**：

```text
手机 WebView (Capacitor)
  │  加载 file / capacitor 本地静态资源
  │  env.json → https://api.example.com + wss://...
  ├─ HTTP/WS ──▶ 云端 Python 后端（同一套 Reflex State）
  └─ JS Bridge ─▶ Capacitor Plugins（通知、相机…）
```

---

## 3. 模块划分（建议包结构）

```text
src/reflex_capacitor/
  __init__.py          # 导出 CapacitorPlugin, mobile
  config.py            # 默认目录名、CORS origins、环境变量名
  plugin.py            # CapacitorPlugin(Plugin)
  mobile.py            # Python 侧原生桥（对标 desktop.py）
  mobile.pyi           # 类型桩
  cli.py               # Click 入口
  preflight.py         # doctor：Node、JDK、Xcode、Android SDK…
  scaffold/            # 模板：capacitor 工程骨架
    package.json
    capacitor.config.json
    www/.gitkeep
    scripts/inject-bridge.mjs   # 可选：往 index.html 注入 bridge
  assets/
    reflex-capacitor-bridge.js  # 稳定 JS API：window.__REFLEX_CAPACITOR__
```

| 模块 | 对标 desktop | 说明 |
|------|--------------|------|
| `CapacitorPlugin` | `DesktopPlugin` | 只实现 remote；无 window_* / tray / embedded |
| `mobile` | `desktop` | 通知、剪贴板、分享、相机…；无 minimize 等 |
| `cli` | `cli` | 调 `npx cap` 而非 cargo |
| `preflight` | `preflight` | 查 Node/Cap/原生工具链 |
| `bridge.js` | `withGlobalTauri` + `__TAURI__` | 给 Reflex 静态页一个稳定全局对象 |

---

## 4. CapacitorPlugin 职责（对标 DesktopPlugin）

### 4.1 配置字段（建议）

```python
CapacitorPlugin(
    backend_url="https://api.example.com",  # 必填（生产）；None 则用 config.api_url
    app_name=None,                          # 默认 Reflex app_name
    app_id="com.example.myapp",             # 反向域名 bundle id
    web_dir="capacitor/www",                # 静态资源目录（Cap webDir）
    capacitor_dir="capacitor",              # Cap 工程根
    icon="assets/logo.png",
    plugins=(                               # 要安装并暴露给 mobile.* 的 Cap 插件
        "local-notifications",
        "clipboard",
        "haptics",
        "share",
        "status-bar",
        "app",
        "splash-screen",
        "toast",
        "network",
        "device",
        "preferences",
        "filesystem",
        "camera",
        "geolocation",
        "keyboard",
    ),
    # 进阶（二期）
    # push_notifications=False,
    # server_url=None,   # 仅 cap serve / 真机热重载时指向 dev host
)
```

**不做** `backend="embedded"`；若调用方误配，插件应明确报错并指向文档。

### 4.2 插件钩子

与 desktop 相同的两个核心钩子：

1. **`update_env_json`**  
   - 用 `backend_url`（或 `REFLEX_CAPACITOR_DEV_BACKEND_URL`）重写各 `Endpoint` URL。  
   - `EVENT` → `wss://` / `ws://`。  
   - 与 `DesktopPlugin.update_env_json` 逻辑可几乎共用（抽公共函数亦可，但初期复制更简单）。

2. **`post_build`**  
   - 若无 `capacitor/`：从 `scaffold/` 生成工程（`appId`、`appName`、`webDir`）。  
   - 将 Reflex `static_dir` 拷到 `webDir`。  
   - 幂等：按 `plugins=` 维护 `package.json` 依赖托管区；确保 bridge 脚本被注入到 `index.html`。  
   - CORS 警告：检查 `cors_allowed_origins` 是否包含 Capacitor origins。

### 4.3 Capacitor origins（CORS）

常见：

- `capacitor://localhost`（iOS 常见）
- `http://localhost`（Android / 部分配置）
- `https://localhost`（视 `capacitor.config` / 服务器配置）

插件应在文档与 `doctor` / `post_build` 中提示：

```python
cors_allowed_origins=["*", "capacitor://localhost", "http://localhost"]
```

生产建议列出明确 origin，而不是长期依赖 `*`（若后端带 cookie 更要注意）。

---

## 5. CLI 命令设计

| 命令 | 行为 | 对标 |
|------|------|------|
| `reflex-capacitor doctor` | Node、npm、`@capacitor/cli`、JDK、Android SDK / Xcode | `doctor` |
| `reflex-capacitor init` | 若无工程：scaffold + `npm i` + `npx cap add ios/android` | （desktop 在首次 build 隐式 scaffold） |
| `reflex-capacitor sync` | `reflex export --frontend-only` → 拷贝 www → 注入 bridge → `npx cap sync` | export + 配置 |
| `reflex-capacitor run android\|ios` | sync 后 `npx cap run …` | `run` |
| `reflex-capacitor open android\|ios` | 打开 Android Studio / Xcode | — |
| `reflex-capacitor build android\|ios` | sync + 正式构建说明 / 调用 gradle/xcodebuild（可二期） | `build` |
| `reflex-capacitor dev` | 起 `reflex run`，Cap `server.url` 指开发机；真机需局域网 IP | `dev` |

环境变量建议：

- `REFLEX_CAPACITOR_DEV_BACKEND_URL` — 编译前端时烘焙的后端（对标 `REFLEX_DESKTOP_DEV_BACKEND_URL`）
- `REFLEX_CAPACITOR_DEV_SERVER_URL` — Capacitor live reload 的前端地址

---

## 6. 与「复用 reflex_web」的关系

| 资源 | 是否复用 |
|------|----------|
| `*.py` 页面、State、事件 | ✅ 同一套 |
| 已部署的云端后端 | ✅ `backend_url` 指向它 |
| 浏览器专用代码 | ⚠️ 注意：无 `window.__TAURI__`；用 `mobile.*` 并检测是否在 Cap 内 |
| 响应式布局 | ⚠️ 建议补触控/安全区（status bar / notch） |
| 桌面 `desktop.*` 调用 | ❌ 移动端改用 `mobile.*`；可用薄封装按平台分流 |

可选模式（应用层）：

```python
def notify(title, body=""):
    if os.environ.get("REFLEX_NATIVE_SHELL") == "capacitor":
        return mobile.notify(title, body)
    if os.environ.get("REFLEX_NATIVE_SHELL") == "desktop":
        return desktop.notify(title, body)
    return rx.toast(...)  # 纯浏览器降级
```

壳本身不强制统一 API；文档推荐应用层适配即可。

---

## 7. 关键差异：Tauri `__TAURI__` vs Capacitor

| | Tauri 2 | Capacitor |
|--|---------|-----------|
| 全局对象 | `withGlobalTauri` → `window.__TAURI__` | 默认有 `window.Capacitor`，但 **插件通常要 `registerPlugin` / 打包导入** |
| Reflex 静态导出 | 无 Vite 插件链接入 `@capacitor/*` npm 包 | **必须自备 bridge 脚本** 注入到 `www/index.html` |
| 权限模型 | capabilities JSON | Info.plist / AndroidManifest + 运行时 permission API |
| 安装插件 | Cargo.toml + main.rs 托管区 | `package.json` + `npx cap sync` |

因此 **`assets/reflex-capacitor-bridge.js` + `window.__REFLEX_CAPACITOR__` 是一等公民**，地位等同 desktop 的 `with_global_tauri=True`。详见 [02-native-bridge.md](02-native-bridge.md)。
