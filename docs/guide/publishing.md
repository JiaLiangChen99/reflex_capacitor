# 发布与签名

> 最后更新：2026-08-25 · 命令细节见 [cli.md](cli.md) · 总索引 [README.md](../README.md)

将 Reflex + Capacitor 应用打成可上架的 release 包（Google Play / App Store）。

## 命令概览

```bash
# Release APK（需签名配置）
reflex-capacitor build android

# Play Store 推荐：AAB
reflex-capacitor build android --format aab

# Debug APK（与 CI 相同，无需 keystore）
reflex-capacitor build android --debug

# iOS（仅 macOS + Xcode）
reflex-capacitor build ios
```

`build` 会先 `sync`（export + cap sync），再调用 Gradle / `cap build`。

---

## Android 签名

### 1. 生成 keystore（一次性）

```bash
keytool -genkey -v -keystore release.keystore -alias myapp -keyalg RSA -keysize 2048 -validity 10000
```

将 `release.keystore` 放在安全位置（**不要提交到 git**）。

### 2. 配置环境变量（推荐）

| 变量 | 说明 |
|------|------|
| `REFLEX_CAPACITOR_KEYSTORE_PATH` | keystore 绝对路径 |
| `REFLEX_CAPACITOR_KEYSTORE_PASSWORD` | keystore 密码 |
| `REFLEX_CAPACITOR_KEY_ALIAS` | 别名（如 `myapp`） |
| `REFLEX_CAPACITOR_KEY_PASSWORD` | 密钥密码 |

Windows PowerShell 示例：

```powershell
$env:REFLEX_CAPACITOR_KEYSTORE_PATH = "D:\keys\release.keystore"
$env:REFLEX_CAPACITOR_KEYSTORE_PASSWORD = "****"
$env:REFLEX_CAPACITOR_KEY_ALIAS = "myapp"
$env:REFLEX_CAPACITOR_KEY_PASSWORD = "****"
reflex-capacitor build android --format aab
```

或使用 CLI 参数：`--keystore-path` / `--keystore-password` / `--key-alias` / `--key-password`。

### 3. Gradle 做了什么

`build` 会写入 `capacitor/android/keystore.properties`，并幂等补丁 `android/app/build.gradle`（标记块 `reflex-capacitor signing`），然后执行：

- APK：`./gradlew assembleRelease`
- AAB：`./gradlew bundleRelease`

产物路径：

- APK：`capacitor/android/app/build/outputs/apk/release/`
- AAB：`capacitor/android/app/build/outputs/bundle/release/`

### 4. 版本号

在 `capacitor/android/app/build.gradle` 的 `defaultConfig` 中调整：

- `versionCode` — 整数，每次上架递增
- `versionName` — 显示版本（如 `1.0.1`）

`cap sync` 不会覆盖这些字段；可在 CI 里用脚本 bump。

---

## Google Play 上架流程（简要）

1. [Google Play Console](https://play.google.com/console) 创建应用
2. 使用 **AAB**（`--format aab`）上传至「正式版 / 测试轨道」
3. 填写商店 listing、内容分级、隐私政策
4. 后端必须是 **HTTPS + WSS**（`CapacitorPlugin(backend_url="https://…")`）
5. 在 Environment `production` 配置 `REFLEX_BACKEND_URL` 后打 release 包（见 [ci.md](ci.md)）

---

## iOS（需 Mac）

1. Apple Developer 账号 + Xcode
2. `reflex-capacitor init --platform ios`
3. Xcode 打开：`reflex-capacitor open ios`
4. 配置 Signing & Capabilities（Team、Bundle ID）
5. `reflex-capacitor build ios` 或 Xcode → Archive

远程后端生产环境同样要求 HTTPS/WSS。局域网 HTTP 仅用于开发（见 [dev-reload.md](dev-reload.md)）。

---

## CI Release（GitHub Actions）

仓库提供可选 workflow **Android Release AAB**（`workflow_dispatch`）：

- Environment：`production`
- Secrets：
  - `REFLEX_BACKEND_URL` — 生产 HTTPS 后端
  - `ANDROID_KEYSTORE_BASE64` — keystore 文件 base64
  - `ANDROID_KEYSTORE_PASSWORD`
  - `ANDROID_KEY_ALIAS`
  - `ANDROID_KEY_PASSWORD`

详见 [ci.md](ci.md#release-aab-可选)。

---

## 安全检查清单

- [ ] keystore 与密码仅存在 CI secrets / 本机，不进仓库
- [ ] 生产 `backend_url` 为 HTTPS
- [ ] `cors_allowed_origins` 生产环境不用 `*`（改为具体域名 + Capacitor origins）
- [ ] Play / App Store 隐私说明与 App 实际权限一致（见 [permissions.md](permissions.md)）

## 相关

- [cli.md](cli.md) · [ci.md](ci.md) · [android-build.md](android-build.md) · [configuration.md](configuration.md) · [README.md](../README.md)
