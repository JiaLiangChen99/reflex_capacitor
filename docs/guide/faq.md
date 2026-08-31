# 常见问题（FAQ）

> 最后更新：2026-08-25 · 总索引 [README.md](../README.md)

更细的排障 → [debug.md](debug.md) · [android-build.md](android-build.md)。

---

### `check` / `doctor` 报缺 JDK / SDK，CLI 能自动装吗？

**不能。** 只检查并打印安装提示（决策 D7）。请自行安装后设 `JAVA_HOME` / `ANDROID_HOME`。见 [install.md](install.md)、[cli.md](cli.md)。

---

### 默认会装哪些原生插件？

默认是 `ALL_PLUGIN_IDS`（相机、定位、TTS、录音等）。**推送不在默认里**，需 `PHASE5_PLUGIN_IDS`。想瘦身再显式传 `CORE_PLUGIN_IDS`。见 [configuration.md](configuration.md)。

---

### 页面能开，但计数器 / State 不更新？

多半是 WebSocket 或后端地址问题：

1. 后端是否 `--backend-host 0.0.0.0`
2. 手机与 PC 是否同网；防火墙是否放行端口
3. `backend_url` 是否为局域网 IP（不是 `127.0.0.1`）
4. HTTP 时是否已 sync（cleartext / `androidScheme`）

见 [configuration.md](configuration.md)、[debug.md](debug.md)。

---

### 换了 `backend_url` 手机还是连旧地址？

前端 URL 在 **export 时烘焙**进静态资源。改完后必须重新：

```bash
reflex-capacitor sync
# 或 build / run（默认会 sync）
```

原理 → [packaging.md](../design/packaging.md)。

---

### npm / Gradle 很慢，要开代理吗？

默认**不开**。需要时：

```bash
reflex-capacitor sync --proxy http://127.0.0.1:7890
```

见 [cli.md](cli.md)。

---

### 远程推送一定要接 FCM 吗？

不一定。App **在线**时可用 WebSocket + `mobile.notify()`（本地通知）。  
系统级离线推送才需要 FCM/APNs，且为可选插件。见 [push-notifications.md](push-notifications.md)。

---

### Windows 能做 iOS 吗？

不能打 iOS 包；需 Mac + Xcode。Android 可在 Windows/Linux 完成。见 [configuration.md](configuration.md#平台检测ios--android)。

---

### PyPI 上的包和本仓库 demo 有什么差别？

库本身不含你的 `capacitor/android` 工程（`init` 生成）。  
本仓库 `demo/` + `PHASE5` 仅为演示；对外默认已是 `ALL_PLUGIN_IDS`、不含推送。见 [install.md](install.md)。

---

## 相关

- [00-getting-started.md](00-getting-started.md) · [install.md](install.md) · [cli.md](cli.md) · [README.md](../README.md)
