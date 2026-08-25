# reflex-capacitor 文档

**remote** 模式：Reflex 静态前端进 Capacitor 壳，连远端 Python 后端。

| 目录 | 读者 | 说明 |
|------|------|------|
| **[guide/](guide/)** | 使用者 | 安装、配置、CLI、打包、API、调试 |
| **[design/](design/)** | 维护者 | 架构、打包原理、规划、测试（**不进 PyPI 包**） |

👉 首读：[guide/00-getting-started.md](guide/00-getting-started.md) · [guide/faq.md](guide/faq.md)

---

## guide/ — 用户文档（推荐）

| 文档 | 用途 |
|------|------|
| [00-getting-started.md](guide/00-getting-started.md) | 快速上手 |
| [install.md](guide/install.md) | pip / 依赖 / PyPI / 推送 GitHub 前检查 |
| [faq.md](guide/faq.md) | 常见问题 |
| [cli.md](guide/cli.md) | 命令行 |
| [configuration.md](guide/configuration.md) | `CapacitorPlugin`、CORS、平台 |
| [android-build.md](guide/android-build.md) | 本机打 APK |
| [02-native-bridge.md](guide/02-native-bridge.md) | `mobile.*` API |
| [dev-reload.md](guide/dev-reload.md) | 真机开发 |
| [debug.md](guide/debug.md) | 排障 |
| [publishing.md](guide/publishing.md) | 签名与上架 |
| [ci.md](guide/ci.md) | GitHub Actions 打 APK |

**按需阅读**（可选能力）：[permissions.md](guide/permissions.md) · [deep-linking.md](guide/deep-linking.md) · [push-notifications.md](guide/push-notifications.md)

---

## design/ — 架构与规划（仓库内）

| 文档 | 用途 |
|------|------|
| [01-architecture.md](design/01-architecture.md) | 三层架构 |
| [packaging.md](design/packaging.md) | export → sync 数据流 |
| [plan.md](design/plan.md) | ADR + 路线图 |
| [testing.md](design/testing.md) | L1/L3 测试 |

[CHANGELOG.md](../CHANGELOG.md) · [README.md](../README.md)
