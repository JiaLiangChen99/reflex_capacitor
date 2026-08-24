# 开发要点与阶段计划

## 1. 实现前必须钉死的决策

| # | 决策 | 建议 |
|---|------|------|
| D1 | 后端模式 | **仅 remote**；拒绝 embedded |
| D2 | Cap 大版本 | 锁定 **Capacitor 6 或 7**（实现时选当前 LTS，写入 `package.json` 引擎） |
| D3 | 原生调用面 | 统一 `window.__REFLEX_CAPACITOR__`，不让业务直接拼插件名 |
| D4 | 配置源 | `rxconfig.CapacitorPlugin` 每次 sync 幂等应用；托管区外可手改 |
| D5 | 包管理 | Cap 工程用 **npm**（与官方一致）；Python 侧 hatchling 打包 bridge 与 scaffold |
| D6 | 与 desktop 共存 | 允许同一仓库同时挂 `DesktopPlugin` + `CapacitorPlugin`（不同目录 `tauri/` vs `capacitor/`） |

---

## 2. 从 reflex-desktop 可「抄」与「改」的清单

### 可直接借鉴（逻辑级复制）

| 来源 | 用途 |
|------|------|
| `DesktopPlugin.update_env_json` | 按 base URL 重写 Endpoint；EVENT→ws/wss |
| `DesktopPlugin._warn_if_cors_blocks` | 改成 Capacitor origins |
| `desktop.py` 的 `rx.call_script` + `callback` 模式 | `mobile.py` 骨架 |
| `desktop.py` 的 `json.dumps` 传参 | 避免注入 |
| CLI：`_find_plugin` / `_reflex_cmd` / export `--frontend-only` | 同一流水线 |
| `preflight` 结构 | 换成 Node/Android/iOS 检查项 |
| Example 的 feature_card + 原生按钮页 | 验证桥 |

### 必须重写

| desktop | capacitor |
|---------|-----------|
| `scaffold/*/src-tauri` Rust | `scaffold/` Node Cap 工程 |
| `_apply_conf` → tauri.conf.json | → capacitor.config.json + package.json |
| `_apply_plugins` Cargo/main.rs 托管区 | npm deps + `cap sync` + plist/manifest 片段 |
| `_apply_capabilities` | iOS/Android 权限模板 |
| `runtime.assemble` / PyO3 | **删除** |
| `cargo build` / `tauri` | `npx cap run/sync` |
| `withGlobalTauri` | 注入 `reflex-capacitor-bridge.js` |

### 明确不做

- 系统托盘、窗口拖拽、maximize、embedded Python、deb/msi、Tauri updater  
- 把 Reflex 组件库改成「移动组件库」（除非后续单独产品）

---

## 3. 开发要点（容易踩坑）

### 3.1 后端 URL 与 WebSocket

- 生产必须用 **HTTPS + WSS**（ATS / Android cleartext 限制）。
- 不要用会被改写的含糊 `localhost` 指向云端；用完整公网域名（desktop 对 `127.0.0.1` 的教训在移动端变成「必须公网或显式局域网 IP」）。
- `dev` 真机：电脑与手机同网；`backend_url` / Cap `server.url` 用局域网 IP，并开放防火墙端口。

### 3.2 CORS / Cookie

- Cap WebView origin ≠ 后端 origin → 必配 `cors_allowed_origins`。
- 若用 cookie 会话：检查 `SameSite`、是否需要 `capacitor://` 特殊处理；很多团队改用 **token 头** 更省事。

### 3.3 静态资源路径

- Reflex export 的 `assets/` 相对路径在 `file` / capacitor 协议下是否正确，要用真机验。
- Bridge 脚本路径用相对 `./assets/...`，注入幂等。

### 3.4 权限时机

- 通知 / 相机 / 定位：**点击时请求**，避免一启动弹一堆权限（审核与体验）。
- Bridge 内统一 permission 流程，Python API 保持简单。

### 3.5 本地文件语义 ≠ 桌面 embedded

- 云端后端 **打不开** 手机上的 `/data/...` 路径。
- `take_photo` / `pick_file` 应回传可序列化内容（dataUrl/base64）或先上传再把 URL 进 State。

### 3.6 安全区与 UI

- `status-bar` + CSS `env(safe-area-inset-*)`；文档提醒 Web 布局适配。
- 不要假设 hover；主流程可达触控。

### 3.7 商店与推送（P2）

- 推送需 Apple/Google 证书与后台；不要放进 MVP 关键路径。
- 本地通知 P0 足够演示「对标 desktop.notify」。

---

## 4. 建议的代码落地顺序（阶段）

### Phase 0 — 文档与骨架

- [x] `docs/` 架构、桥、计划  
- [x] `pyproject.toml`、包 `src/reflex_capacitor`、README  

### Phase 1 — MVP 可跑通（联网壳）✅

目标：现有 Reflex Web → 真机打开并连上云端后端。

1. [x] `CapacitorPlugin`：`update_env_json` + `post_build`（拷贝 www）  
2. [x] `scaffold` + `init`：生成 Cap 工程、`cap add android`（Windows 上 iOS 需 macOS）  
3. [x] CLI：`doctor` / `init` / `sync` / `run` / `open`  
4. [x] CORS 警告  
5. [x] `demo/` 最小计数器 + `CapacitorPlugin`  

**验收**：`reflex-capacitor sync` 产出 `capacitor/www` + `android/`；配置 `backend_url` 后真机连远程后端。（已于 2026-08-24 验证通过。）

> 后续 Phase 2–4 详细待办见 **[04-roadmap.md](04-roadmap.md)**。

### Phase 2 — 原生桥 P0

1. `reflex-capacitor-bridge.js` + HTML 注入  
2. `mobile.py`：`notify`, `toast`, `haptics_*`, `share`, `clipboard_*`, `status_bar_*`, `splash_hide`, `device_info`, `network_status`, `app_exit`  
3. `plugins=` 驱动 npm 安装与权限模板  
4. Example Native 页  

**验收**：按钮弹出本地通知；分享面板可调起。

### Phase 3 — 原生桥 P1 + dev 体验

1. `camera` / `geolocation` / `filesystem` / `preferences` / `keyboard`  
2. `reflex-capacitor dev`（server.url + 烘焙 DEV_BACKEND_URL）  
3. `mobile.invoke` + 自定义插件文档  
4. `mobile.pyi`、单元测试（脚本生成快照 / CORS 检测）  

### Phase 4 — 加固

1. `build` 产出签名包说明（对标 desktop 的 signing 文档，但走 Android/iOS 官方流程）  
2. 推送（可选）  
3. 深链 / 返回键 → State  
4. CI：至少 Android debug 构建  

---

## 5. `CapacitorPlugin` / CLI 伪流程

```text
reflex-capacitor sync
  1. preflight（可 --skip）
  2. 设置环境：无；读 CapacitorPlugin
  3. reflex export --frontend-only
       → Plugin.update_env_json 烘焙 api/ws
       → Plugin.post_build：
            scaffold if needed
            copy static → capacitor/www
            ensure bridge.js injected
            ensure package.json plugins
  4. npm install（在 capacitor/）
  5. npx cap sync
```

```text
reflex-capacitor run android
  1. sync
  2. npx cap run android
```

---

## 6. 测试策略

| 层级 | 内容 |
|------|------|
| 单元 | `update_env_json` URL；HTML 注入幂等；CORS 检测函数 |
| 集成 | 临时目录 scaffold；`package.json` 含声明插件 |
| 手工 | Android 模拟器连 staging 后端；通知/分享/剪贴板 |
| 回归 | Example App 与文档步骤一致 |

Windows 开发者：**Android 为主验收**；iOS 在 CI macOS 或文档标注限制。

---

## 7. 文档交付物（实现期要补的）

| 文档 | 用途 |
|------|------|
| 根 `README.md` | 快速开始（对标 reflex-desktop README） |
| `docs/01–03` | 设计（已有） |
| `docs/permissions.md` | 各插件权限文案模板 |
| `docs/dev-reload.md` | 真机热重载与局域网 |
| `docs/publishing.md` | 上架要点（证书、隐私清单） |

---

## 8. 工作量粗估（1 人熟悉 Reflex + 略懂 Cap）

| 阶段 | 粗估 |
|------|------|
| Phase 1 MVP 壳 | 3–5 天 |
| Phase 2 P0 桥 | 3–5 天 |
| Phase 3 P1 + dev | 4–7 天 |
| Phase 4 加固 | 持续 |

最大风险不在 Python，而在：**bridge 与 Cap 版本绑定、真机 CORS/WS、权限清单、各机 WebView 差异**。

---

## 9. 验收时的「最小用户故事」

```text
作为 Reflex 开发者：
  1. 已有线上 Reflex 网站
  2. pip install reflex-capacitor
  3. rxconfig 增加 CapacitorPlugin(backend_url="https://…", app_id="…")
  4. reflex-capacitor init && reflex-capacitor run android
  5. 手机上操作与网站相同；点「通知」出现系统通知
```

满足以上，即视为对标 `reflex-desktop` remote + `desktop.notify` 的移动端成功路径。
