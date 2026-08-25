# 规划与决策

> 最后更新：2026-08-25 · 维护者文档（**不含在 PyPI sdist**）  
> 用户操作见 [guide/](../guide/) · 版本变更见 [CHANGELOG.md](../../CHANGELOG.md)

---

## 已采纳决策（ADR 摘要）

| # | 主题 | 决策 |
|---|------|------|
| D1 | 后端 | **仅 remote**；不做 embedded Python |
| D2 | Capacitor | 锁定 **7.x** |
| D3 | 原生桥 | `window.__REFLEX_CAPACITOR__` + `mobile.*` |
| D4 | 配置 | `rxconfig` 幂等写托管区 |
| D5 | 依赖 | Cap 用 npm；Python 用 hatchling |
| D6 | 共存 | 可与 `DesktopPlugin` 同仓 |
| D7 | 宿主工具链 | **只检查、不代装** SDK/JDK/Node |
| D8 | 推送 | **非默认**；`PHASE5_PLUGIN_IDS` 显式启用 |
| D9 | 代理 | CLI 默认无代理；`--proxy` 显式开启 |
| D10 | 主平台 | **Android**；iOS 需 Mac |

**明确不做**：embedded Python、窗口 tray、移动 UI 组件库、代装系统 SDK、默认捆绑 FCM。

---

## 已交付（Phase 1–5 ✅）

| Phase | 内容 |
|-------|------|
| 1 | 壳 + remote 后端 + CLI 骨架 |
| 2 | bridge + `mobile.*` P0 + 插件托管 |
| 3 | P1 + `dev` + 反向事件 + 图片编辑器 |
| 4 | release 构建 + 签名文档 + CI |
| 5 | 深链/推送（可选）+ 测试 + iOS plist |

---

## 下一步

1. PyPI 发版与文档维护（见 [install.md](../guide/install.md)）
2. iOS 真机 / macOS CI
3. 定位等机型稳定性（见 [debug.md](../guide/debug.md)）
4. 按需社区插件（生物识别、条码等）
5. 可选：`deep_link_scheme=` 自动写 Manifest

---

## 相关

- [01-architecture.md](01-architecture.md) · [packaging.md](packaging.md) · [testing.md](testing.md)
