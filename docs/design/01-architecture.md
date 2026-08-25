# 架构设计：对标 reflex-desktop

> 最后更新：2026-08-25  
> 操作手册 → [00-getting-started.md](../guide/00-getting-started.md) · 打包数据流 → [packaging.md](packaging.md) · 决策 → [plan.md](plan.md)

## 1. reflex-desktop 在做什么（对齐点）

Reflex 应用 = **静态前端 SPA** + **Python ASGI 后端**。

| 层 | desktop | capacitor（本项目） |
|----|---------|---------------------|
| Reflex 插件 | `DesktopPlugin` | `CapacitorPlugin` |
| Python→原生桥 | `desktop.*` → `__TAURI__` | `mobile.*` → `__REFLEX_CAPACITOR__` |
| CLI | export + cargo/tauri | export + npm / `npx cap` / Gradle |

继承的关键决策：

1. **`rxconfig` 是唯一配置源** — 幂等重写托管区。
2. **后端地址写进静态 env** — `EVENT` → `ws://` / `wss://`。
3. **原生能力是事件桥，不是 UI 组件库**。
4. **CORS** — WebView origin 与 API 不同源。
5. **dev ≠ 生产壳** — live reload 可选；默认 run/build 用导出静态资源。

刻意不做：embedded Python、窗口控件、Tauri updater。

---

## 2. reflex-capacitor 目标架构

```text
┌─────────────────────────────────────────────────────────────┐
│ 开发者 Reflex 工程                                           │
│  rxconfig.py  →  plugins=[CapacitorPlugin(backend_url=...)] │
│  app/*.py     →  from reflex_capacitor import mobile        │
└───────────────────────────┬─────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
  CapacitorPlugin     mobile (api)         CLI
  update_env_json     rx.call_script   init/sync/run/
  post_build          → __REFLEX_CAP__ build/dev/doctor
         │                  │                  │
         └────────┬─────────┴────────┬─────────┘
                  ▼                  ▼
         <app>/capacitor/     云端 Reflex 后端
           www/  android/ ios/
```

**运行时（remote）**：

```text
手机 WebView
  │  加载本地 www + env（api / wss）
  ├─ HTTP/WS ──▶ 云端 Python 后端
  └─ JS Bridge ─▶ Capacitor Plugins
```

---

## 3. 模块划分（当前包结构）

```text
src/reflex_capacitor/
  plugin.py            # CapacitorPlugin
  cli.py               # Click 入口
  preflight.py         # doctor / 命令前检查
  network_env.py       # 子进程代理策略
  config.py            # 目录名、CORS origins、Cap 版本
  android_signing.py   # release 签名
  bridge/
    api.py / api.pyi   # mobile.*
    inject.py          # bridge 注入
    plugins.py         # 插件 id → npm / 权限
    assets/bridge.js
    ios_plist.py
  components/          # 可选 UI（如图片编辑器）
  scaffold/            # Cap 工程模板
```

| 模块 | 说明 |
|------|------|
| `CapacitorPlugin` | remote only；烘焙 URL、scaffold、拷贝 www |
| `mobile` | 通知、相机、定位、推送注册等事件桥 |
| `cli` + `preflight` | 编排构建；宿主依赖只报不装 |
| `bridge.js` | 稳定全局 API，地位对齐 desktop 的 global Tauri |

---

## 4. CapacitorPlugin 职责

### 4.1 配置

见 [configuration.md](../guide/configuration.md)。要点：`backend_url`、`app_id`、`plugins=` 分层（CORE / EXTENDED / PHASE5）。

### 4.2 钩子

1. **`update_env_json`** — 按 `backend_url` / dev 环境变量重写 Endpoint；EVENT→ws/wss。  
2. **`post_build`** — scaffold、拷贝静态资源、插件依赖托管区、bridge 注入、CORS 警告；HTTP 时 cleartext。

### 4.3 CORS origins

常见：`capacitor://localhost`、`http://localhost`、`https://localhost`。生产勿长期 `*`。

---

## 5. CLI（摘要）

完整选项 → [cli.md](../guide/cli.md)。命令前按场景跑 `preflight`（Android build 要 JDK+SDK；run/dev 还要 adb）。

环境变量：`REFLEX_CAPACITOR_DEV_BACKEND_URL`、`REFLEX_CAPACITOR_PROXY`、签名相关 `REFLEX_CAPACITOR_KEYSTORE_*`。

---

## 6. 与现有 Reflex Web 的关系

| 资源 | 是否复用 |
|------|----------|
| 页面 / State / 事件 | ✅ |
| 已部署云端后端 | ✅ `backend_url` |
| `desktop.*` | ❌ 移动端用 `mobile.*` |
| 布局 | ⚠️ 补安全区与触控 |

---

## 7. Tauri vs Capacitor（桥为什么必要）

| | Tauri 2 | Capacitor |
|--|---------|-----------|
| 全局对象 | `__TAURI__` | 需自备 bridge；`Capacitor.Plugins` 不自动进 Reflex bundle |
| 权限 | capabilities | Manifest / Info.plist |
| 装插件 | Cargo | `package.json` + `cap sync` |

因此 **`bridge.js` + `__REFLEX_CAPACITOR__` 是一等公民** → [02-native-bridge.md](../guide/02-native-bridge.md) · [packaging.md](packaging.md)。
