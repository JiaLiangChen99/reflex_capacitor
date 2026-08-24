# CI：按 GitHub Environment Secret 打 Android 调试包

本机不装 Android Studio 时，用 Actions 产出 **debug APK**。  
**后端地址不写在 workflow 里**，而是写在各 Environment 的 Secret 里，方便 lan / staging / production 切换。

## 一次配置（每个环境做一遍）

1. 仓库 **Settings → Environments → New environment**，建议建三个：

   | Environment 名 | 用途 | Secret `REFLEX_BACKEND_URL` 示例 |
   |----------------|------|----------------------------------|
   | `lan` | 家里真机连电脑后端 | `http://192.168.1.56:8001` |
   | `staging` | 测试服 | `https://staging-api.example.com` |
   | `production` | 正式服 | `https://api.example.com` |

2. 进入某个 Environment → **Environment secrets** → **Add secret**  
   - Name：`REFLEX_BACKEND_URL`（固定这个名字）  
   - Value：该环境的后端 base URL（不要末尾斜杠）

3. push / PR 默认使用 Environment **`staging`**（需已配置上述 Secret）。  
   手动跑包： **Actions → Android APK → Run workflow** → 选择 `lan` / `staging` / `production`。

> Secret 名必须是 `REFLEX_BACKEND_URL`。缺了会直接失败并提示去 Environments 里配置。

## 下载与安装

1. 进入该次 run → **Artifacts** → `app-debug-<环境名>`  
2. 解压得到 `app-debug.apk`，传到手机安装（允许未知来源）

可选 USB：

```bash
adb install -r app-debug.apk
```

## 流程

```text
选择 Environment (lan | staging | production)
  → 读取该环境的 secrets.REFLEX_BACKEND_URL
  → uv sync + reflex-capacitor init/sync（烘焙后端 URL）
  → ./gradlew assembleDebug
  → 上传 Artifact: app-debug-<env>
```

`http://` 后端会打开 Capacitor `server.cleartext`；生产请用 **HTTPS**。

## 注意

- debug 包仅测试，不上架。  
- 手机必须能访问该 Environment 里配置的 URL（`lan` 时手机与电脑同一 Wi‑Fi）。  
- `capacitor/` 被 gitignore，CI 每次重新生成，无需提交 android 工程。  
- 本地 `rxconfig.py` 的 `backend_url` 只影响本机 `sync`/`run`；**CI 一律以 Secret 为准**（`REFLEX_CAPACITOR_DEV_BACKEND_URL` 覆盖）。
