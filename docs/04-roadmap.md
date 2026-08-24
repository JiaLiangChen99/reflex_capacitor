# 路线图：Phase 1 回顾 + Phase 2–4 待办

> 最后更新：2026-08-24  
> Phase 1（壳 + remote 后端）已在真机验证通过。本文记录后续阶段，避免遗忘。

相关文档：

- 架构总览 → [01-architecture.md](01-architecture.md)
- 原生桥 API 设计 → [02-native-bridge.md](02-native-bridge.md)
- 开发踩坑 → [03-development-plan.md](03-development-plan.md)
- CI 打 APK → [ci.md](ci.md)

---

## Phase 1 — 已完成 ✅

**目标**：Reflex 静态前端进 Capacitor 壳，连远程 Python 后端（State / WebSocket 正常）。

| 项 | 状态 | 说明 |
|----|------|------|
| `CapacitorPlugin.update_env_json` | ✅ | 烘焙 `http(s)://` + `ws(s)://` |
| `CapacitorPlugin.post_build` | ✅ | scaffold + 拷贝 `www/` |
| CLI `doctor` / `init` / `sync` / `run` / `open` | ✅ | |
| CORS 警告 | ✅ | `CAPACITOR_ORIGINS` |
| HTTP LAN 后端 | ✅ | `cleartext` + `androidScheme: http` + Manifest 补丁 |
| GitHub Actions debug APK | ✅ | 见 [ci.md](ci.md) |
| 移动端 demo（底栏 + 计数） | ✅ | `demo/demo.py` |
| `demo/__init__.py` | ✅ | 修复 `demo.demo` 导入 |

### Phase 1 相对架构文档仍缺（不阻塞，记入后续）

| 项 | 计划阶段 |
|----|----------|
| `mobile.py` / `mobile.pyi` | Phase 2 |
| `reflex-capacitor-bridge.js` + HTML 注入 | Phase 2 |
| `CapacitorPlugin(plugins=(...))` | Phase 2 |
| `CapacitorPlugin(icon=...)` | Phase 2 ✅ |
| `reflex-capacitor dev` | Phase 3 |
| `reflex-capacitor build`（release） | Phase 4 |
| 单元测试 | Phase 2 ✅（基础） / Phase 3（扩展） |
| CI 恢复 Environment Secret | Phase 2 ✅ |
| iOS 真机验证 | Phase 3 |

### Phase 1 踩坑备忘（已实现，文档化）

1. **WebSocket timeout**：`androidScheme: https` + `ws://` 混合内容被拦 → HTTP 后端必须 `androidScheme: http`。
2. **HTTP 明文**：需 `cleartext: true` + `usesCleartextTraffic="true"`。
3. **Windows 防火墙**：手机访问 LAN 端口需放行入站（如 TCP 8001）。
4. **后端绑定**：`reflex run --backend-only` 需 `0.0.0.0`，不能仅 `127.0.0.1`。
5. **Python 包**：`app_name="demo"` 时目录需 `demo/__init__.py`。

---

## Phase 2 — 原生桥 P0 ✅

**目标**：对标 `reflex-desktop` 的 `desktop.py`——从 Reflex 事件调系统能力（**不是**新 UI 组件库）。

**验收标准**（已通过）：

- demo 有「原生」页：点按钮弹出通知、分享、震动。
- `from reflex_capacitor import mobile` 可用，带 `bridge/api.pyi`。
- 打包后 `index.html` 注入 bridge，真机 `window.__REFLEX_CAPACITOR__` 存在。

### 2.1 Bridge 基础设施

- [x] `src/reflex_capacitor/bridge/assets/bridge.js`（原规划路径已改为 `bridge/` 目录）
  - [x] 挂载 `window.__REFLEX_CAPACITOR__`
  - [x] `isNative()` / `platform()` 探测
  - [x] 浏览器降级（`reflex run` 不报错）
- [x] `post_build` / `sync` 后幂等注入：
  - [x] 复制 bridge → `www/assets/reflex-capacitor/bridge.js`
  - [x] `index.html` 插入 `<script>`（marker 注释，可重复 sync）
- [x] `CapacitorPlugin.plugins: tuple[str, ...]`
  - [x] 映射到 `@capacitor/<name>` npm 包
  - [x] 写 `package.json` 托管区（幂等）
  - [x] `npx cap sync` 拉原生依赖
- [x] 默认开箱插件集（见 [02-native-bridge.md §7](02-native-bridge.md)）

### 2.2 `mobile.py` P0 API

| 函数 | Cap 插件 | 备注 |
|------|----------|------|
| `notify(title, body="")` | local-notifications | 先 requestPermissions |
| `toast(text, duration=...)` | toast | |
| `haptics_impact(style=...)` | haptics | |
| `haptics_notification(type=...)` | haptics | |
| `share(title, text, url, dialog_title)` | share | |
| `clipboard_write(text)` | clipboard | |
| `clipboard_read(callback)` | clipboard | |
| `status_bar_set_style(style)` | status-bar | light / dark |
| `status_bar_hide()` / `status_bar_show()` | status-bar | |
| `splash_hide()` | splash-screen | 启动后隐藏 |
| `device_info(callback)` | device | |
| `network_status(callback)` | network | |
| `app_exit()` | app | |

- [x] 实现上述 API（`rx.call_script` → `__REFLEX_CAPACITOR__`）
- [x] `api.pyi` 类型桩（位于 `bridge/api.pyi`）
- [x] `__init__.py` 导出 `mobile`

### 2.3 权限与清单

- [x] 新建 [permissions.md](permissions.md)（各插件 Android / iOS 权限模板）
- [x] `finalize_bridge` 按 `plugins=` 写入 Android Manifest（通知权限）
- [x] Bridge 内统一「点击时再请求权限」（notify 等）

### 2.4 Demo + CI 收尾

- [x] demo 增加「原生」Tab（notify / share / haptics / clipboard / device / network）
- [x] CI：GitHub Environment secret `REFLEX_BACKEND_URL`（lan / staging / production）
- [x] CI：staging / production 用 HTTPS，lan 用 HTTP + 校验 `androidScheme`

### 2.5 可选（时间允许）

- [x] `CapacitorPlugin(icon="assets/icon.png")` → 复制到 Android mipmap
- [x] 简单单元测试：bridge 注入幂等、env 烘焙 URL、http/https scheme

**粗估**：3–5 人天。

---

## Phase 3 — 原生桥 P1 + 开发体验

**目标**：常用设备能力 + 真机热重载 + 可扩展 + 测试。

### 3.1 `mobile.py` P1 API

| 函数 | Cap 插件 | 注意 |
|------|----------|------|
| `take_photo(callback, quality=...)` | camera | 回传 dataUrl，不上传路径 |
| `pick_images(callback, ...)` | camera | 同上 |
| `get_current_position(callback)` | geolocation | 运行时权限 |
| `pref_set(key, value)` | preferences | |
| `pref_get(key, callback)` | preferences | |
| `fs_read` / `fs_write` | filesystem | 沙箱路径，非用户任意路径 |
| `keyboard_show` / `keyboard_hide` | keyboard | |
| `browser_open(url)` | browser | 应用内浏览器 |
| `invoke(name, args, callback=)` | 自定义插件 | 扩展缝 |

- [x] 实现 P1 API（bridge.js + `mobile.*`）
- [x] demo 演示 P1（偏好 / 相机 / 定位 / 浏览器 / 沙箱文件）
- [ ] demo 演示拍照 / 定位（可选页）→ 已合并进原生 Tab

### 3.2 `reflex-capacitor dev`

- [x] 启动 `reflex run`（默认 `--backend-only`，可选 `--live-reload`）
- [x] 设置 `REFLEX_CAPACITOR_DEV_BACKEND_URL` + Cap `server.url`（live-reload 模式）
- [x] 文档 [dev-reload.md](dev-reload.md)：真机与电脑同网、防火墙、端口
- [x] LAN IP 自动检测 + `--lan-ip` 覆盖

### 3.3 原生 → Reflex 反向事件

- [x] Android 返回键 → `poll_native_events`（`back_button=emit|exit|history`）
- [x] App 前台 / 后台 `appStateChange` + `pause` / `resume`
- [x] 键盘显隐 `keyboardWillShow` / `keyboardWillHide`
- [x] `mobile.setup_native_listeners()` + `mobile.poll_native_events(callback)`
- [x] demo 原生 Tab 演示

### 3.4 质量

- [x] 单元测试：`update_env_json`、http/https scheme、dev server 配置
- [x] 单元测试：bridge 注入、插件列表
- [ ] 集成测试：临时目录 scaffold + `package.json` 含声明插件（可选）
- [ ] iOS：`cap add ios` + 至少模拟器跑通（需 macOS CI 或文档说明）— 见 [dev-reload.md](dev-reload.md)

**粗估**：4–7 人天。

---

## Phase 4 — 加固与发布

**目标**：可上架、可运维、可扩展。

### 4.1 构建与签名

- [ ] CLI `reflex-capacitor build android|ios`（release）
- [ ] 文档 [publishing.md](publishing.md)：
  - [ ] Android：keystore、`.aab` / `.apk` 签名
  - [ ] iOS：证书、Provisioning、Archive（需 Mac）
- [ ] CI：可选 release 流水线（secrets 存签名材料）

### 4.2 推送与高级能力（按需）

| 能力 | 插件 | 阶段 |
|------|------|------|
| 远程推送 | push-notifications | P2，需 FCM / APNs 配置 |
| 生物识别 | community | P2 |
| 条码扫描 | community | P2 |
| 应用内浏览器 | browser | P2 |
| 深链 `appUrlOpen` | app | 与 3.3 联动 |

### 4.3 运维与文档

- [ ] CI：多环境 matrix（lan / staging / production）
- [ ] README 对标 reflex-desktop 完整度（命令表、rxconfig 示例、限制说明）
- [ ] CHANGELOG 维护

**粗估**：持续迭代。

---

## 明确不做（全阶段）

| 项 | 原因 |
|----|------|
| `backend="embedded"` / 进程内 Python | 移动端不现实，见 [01-architecture.md](01-architecture.md) |
| 窗口 minimize / tray / 拖拽 | 桌面专属 |
| Reflex 移动 UI 组件库 | 非本项目范围；用 Reflex 响应式 + `mobile.*` 事件桥 |
| 地图 Web Component 封装 | 需要时单独立项 |

---

## 阶段依赖关系

```text
Phase 1 ✅ 壳 + remote 后端
    │
    ▼
Phase 2    bridge.js + mobile.py P0 + plugins= + demo 原生页
    │
    ▼
Phase 3    mobile P1 + dev 热重载 + 反向事件 + 测试 + iOS
    │
    ▼
Phase 4    release 构建 + 签名文档 + 推送等 + CI 加固
```

---

## 快速对照：现在仓库里有什么

| 路径 | Phase |
|------|-------|
| `src/reflex_capacitor/plugin.py` | 1 ✅ + icon |
| `src/reflex_capacitor/cli.py` | 1 ✅ + `dev` (Phase 3) |
| `src/reflex_capacitor/preflight.py` | 1 ✅ |
| `src/reflex_capacitor/bridge/`（api、inject、assets） | 2 ✅ |
| `demo/demo.py` 原生 Tab + P1 + 反向事件 | 3 ✅ |
| `tests/test_inject.py` / `tests/test_plugin.py` | 2 ✅ / 3 ✅ |
| `.github/workflows/android-apk.yml` | 2 ✅（Environment matrix） |
| `docs/permissions.md` / `docs/debug.md` | 2 ✅ |
| `docs/dev-reload.md` | 3 ✅ |
| `docs/publishing.md` | 4 ⬜ |

---

## 下一步：Phase 4（发布加固）

- ⬜ `reflex-capacitor build` release 打包
- ⬜ 推送 / 定位稳定性等按需迭代
- ⬜ iOS 真机 / 模拟器验证（需 Mac）

Phase 3 收尾已完成：`dev` 命令、反向原生事件、文档与测试。
