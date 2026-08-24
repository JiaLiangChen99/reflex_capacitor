# CI：打 Android 调试包（当前写死后端 URL）

> **临时调试**：workflow 写死 `http://192.168.1.56:8001`。

## 为什么会出现 `timeout connect ws://…/_event`

手机浏览器能开 HTTP，App 仍连不上 WebSocket，常见是这两点：

1. **混合内容（本次主因）**  
   Capacitor 默认 `androidScheme: "https"` → 页面来自 `https://localhost`，再去连 `ws://192.168.x.x` 会被 WebView 当成 insecure mixed content 拦掉，表现就是 timeout。  
   **修复**：HTTP 后端时强制 `androidScheme: "http"` + `cleartext: true`。

2. **Windows 防火墙**  
   若手机浏览器也打不开 `http://192.168.1.56:8001/ping`，在 Windows 上放行 Python 入站，或临时关专用网络防火墙试一次。

## 你要确认

1. 后端在跑且是 `0.0.0.0:8001`（不要只绑 `127.0.0.1`）：
   ```bash
   reflex run --env prod --backend-only
   ```
2. 手机浏览器能打开：`http://192.168.1.56:8001/ping`（应返回 `"pong"`）
3. 用**新打的 APK**（含 `androidScheme: http`）覆盖安装后再测

## 跑包

Actions → **Android APK** → Run workflow → `lan` → 下载安装。

CI 会校验：

- env 含 `ws://192.168.1.56:8001/_event`
- `cleartext: true` 且 `androidScheme: "http"`
- Manifest 含 `usesCleartextTraffic="true"`
