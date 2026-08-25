# 打包流水线原理

> 最后更新：2026-08-25  
> 操作步骤见 [cli.md](../guide/cli.md) / [android-build.md](../guide/android-build.md)；本文只讲「为什么」与数据流。

---

## 1. 总览

```text
rxconfig.CapacitorPlugin
        │
        ▼
reflex export --frontend-only
  ├─ update_env_json  →  静态 env 里写入 api_url / ws 端点
  └─ post_build       →  scaffold（若需要）+ 拷贝静态资源到 capacitor/www
        │
        ▼
CLI：npm install（项目依赖）→ 注入 / finalize bridge → npx cap sync
        │
        ▼
原生工程（android/ / ios/）← WebView 加载本地 www
        │
        ▼
Gradle / Xcode 产出 APK·AAB / Archive
```

运行时 WebView **不**跑 Python：State / 事件走远程 HTTP + WebSocket。

---

## 2. 为何必须烘焙 `env.json`

导出的前端是静态文件，没有「启动时再问一次后端端口」的官方通道。  
`CapacitorPlugin.update_env_json` 在 export 时把 `backend_url`（或 `REFLEX_CAPACITOR_DEV_BACKEND_URL`）写进前端配置，并把事件端点改成 `ws://` / `wss://`。

因此：**换后端地址要重新 export/sync**，不能只改手机上的某个运行时开关（`dev --live-reload` 另有 `server.url` 路径，见 [dev-reload.md](../guide/dev-reload.md)）。

---

## 3. 托管区幂等

`rxconfig` 是唯一配置源。sync 会重写约定托管区（如 `package.json` 插件依赖块、capacitor.config 中由插件维护的字段）。  
托管区外的手改（自定义 Gradle、额外 Manifest）应保留——实现上靠标记/合并，而不是每次删光工程。

---

## 4. Bridge 为何单独注入

Reflex export **不会**把 `@capacitor/*` 打进前端 bundle。  
原生侧 `npm i` + `cap sync` 只保证原生插件进 APK；Web 层还需：

1. 复制 `bridge.js` → `www/assets/reflex-capacitor/`
2. 幂等插入 `<script>` 到 `index.html`
3. `finalize_bridge`：从 `node_modules` 拷 vendor、补权限 / Info.plist

业务只调 `window.__REFLEX_CAPACITOR__`（经 `mobile.*`），不直接拼插件名。详见 [02-native-bridge.md](../guide/02-native-bridge.md)。

---

## 5. HTTP 局域网 vs HTTPS 生产

| | LAN `http://` | 生产 `https://` |
|--|---------------|-----------------|
| cleartext | 需要（插件自动） | 不应依赖 |
| `androidScheme` | `http`（避免 ws 混合内容被拦） | 默认安全方案 |
| CORS | WebView origin ≠ API origin | 同左，生产收紧列表 |

这是真机「页面能开但 State/WS 挂」的最常见根因之一。更多边界 → [configuration.md](../guide/configuration.md)。

---

## 6. 宿主检查 vs 项目 npm

| 类型 | 谁负责 | CLI 行为 |
|------|--------|----------|
| Node / JDK / SDK / Xcode | 用户 | `doctor`/`check` + 命令前预检；**不安装** |
| `capacitor/package.json` 依赖 | 项目目录 | `init`/`sync` 执行 `npm install` |
| Gradle 依赖 | 用户 Gradle 缓存 | `build` 调 `./gradlew`；可用 `--proxy` |

---

## 7. 相关模块

| 路径 | 职责 |
|------|------|
| `plugin.py` | `update_env_json` / `post_build` / cleartext |
| `cli.py` | 编排 export、npm、cap、gradle |
| `preflight.py` | 宿主依赖探测 |
| `bridge/` | JS 桥、注入、权限、plist |
| `network_env.py` | 子进程代理策略 |

架构总览 → [01-architecture.md](01-architecture.md)
