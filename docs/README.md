# reflex-capacitor 设计文档

将 Reflex Web 应用包装为 **Capacitor 移动 App**（iOS / Android）的设计与开发要点。

> **范围**：仅 **remote** 模式（静态前端进壳，Python 后端跑在服务器）。不提供桌面版 `embedded`（进程内嵌 CPython）对等物——移动端不现实，也非本项目目标。

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/ci.md](ci.md) | GitHub Actions 打 debug APK（免本机 Android Studio） |
| [01-architecture.md](01-architecture.md) | 对标 reflex-desktop 的架构、模块划分、数据流 |
| [02-native-bridge.md](02-native-bridge.md) | 原生能力清单、与 `desktop.py` 的映射、`mobile.py` API 设计 |
| [03-development-plan.md](03-development-plan.md) | 开发要点、脚手架、CLI、分阶段交付、风险 |

Phase 1（壳 + 远程后端）已落地：见仓库根目录 `README.md` 与 `src/reflex_capacitor/`。

## 一句话目标

```text
同一套 Reflex 页面 / State / 事件
  → reflex export 静态前端
  → Capacitor WebView 加载
  → 连云端 Reflex 后端
  → 需要时用 mobile.* 调 Cap 原生插件（通知、相机、分享…）
```

对用户而言：`pip install reflex-capacitor` 后，在 `rxconfig.py` 挂上 `CapacitorPlugin`，执行 `reflex-capacitor run android|ios` 即可在模拟器/真机打开 App。
