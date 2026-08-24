# CI：打 Android 调试包（当前写死后端 URL）

> **临时调试**：workflow 里写死了 `http://192.168.1.56:8001`，并强制开启 Android
> `usesCleartextTraffic`。原因：手机浏览器能开该 URL，但 App WebView 默认禁止明文 HTTP。

## 你要确认的两件事

1. 电脑上 Reflex 后端监听 **`0.0.0.0:8001`**（不要只绑 `127.0.0.1`），例如：
   ```bash
   reflex run --env prod --backend-only --backend-host 0.0.0.0 --backend-port 8001
   ```
2. 手机与电脑同一 Wi‑Fi；手机浏览器能打开 `http://192.168.1.56:8001`。

## 跑包

Actions → **Android APK** → Run workflow → 选 `lan` → 下载 Artifact 安装。

CI 会校验：

- `reflex-env-*.js` 里含 `192.168.1.56:8001`
- `capacitor.config.json` 含 `"cleartext": true`
- `AndroidManifest.xml` 含 `usesCleartextTraffic="true"`

## 之后改回 Secret

验证通了再把 workflow 改回读 Environment secret `REFLEX_BACKEND_URL`。
HTTPS 生产环境不需要 cleartext。
