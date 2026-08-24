# reflex-capacitor 设计文档

将 Reflex Web 应用包装为 **Capacitor 移动 App**（iOS / Android）的设计与开发要点。

> **范围**：仅 **remote** 模式（静态前端进壳，Python 后端跑在服务器）。  
> **当前进度**：Phase 1–4 核心已完成（2026-08-24），详见 [04-roadmap.md](04-roadmap.md)。

## 从这里开始

👉 **[00-getting-started.md](00-getting-started.md)** — 安装、配置、CI 打 APK、dev、build、文档索引（**推荐首读**）

## 文档索引

| 文档 | 内容 |
|------|------|
| [00-getting-started.md](00-getting-started.md) | **快速上手**（Phase 1–4 总览） |
| [04-roadmap.md](04-roadmap.md) | 各 Phase 完成情况与待办 |
| [01-architecture.md](01-architecture.md) | 架构、模块、数据流 |
| [02-native-bridge.md](02-native-bridge.md) | `mobile.*` API 与 bridge 设计 |
| [03-development-plan.md](03-development-plan.md) | 开发决策与踩坑 |
| [ci.md](ci.md) | GitHub Actions：debug APK / release AAB |
| [dev-reload.md](dev-reload.md) | `reflex-capacitor dev` 真机开发 |
| [publishing.md](publishing.md) | Release 签名、Play 上架、iOS 概要 |
| [debug.md](debug.md) | 真机调试、日志、WebSocket 问题 |
| [permissions.md](permissions.md) | 各插件 Android/iOS 权限 |
| [image-editor.md](image-editor.md) | 内置图片编辑器（本机裁剪/压缩） |

根目录 [README.md](../README.md) · [CHANGELOG.md](../CHANGELOG.md)

## 一句话目标

```text
同一套 Reflex 页面 / State / 事件
  → reflex export 静态前端
  → Capacitor WebView 加载
  → 连远程 Reflex 后端
  → mobile.* 调原生能力（通知、相机、定位…）
```

## 平台支持

| | Android（Windows 可开发） | iOS（需 Mac） |
|--|---------------------------|---------------|
| 本地 CLI | ✅ | ❌ |
| CI 打 debug 包 | ✅ | 未配置 |
| 生产 release | ✅ AAB/APK | 需本机 Xcode |
