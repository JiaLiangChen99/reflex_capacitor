# 本机 Android 构建

> 最后更新：2026-08-25

本文说明在 **本机** 打 debug/release APK 所需环境。CI 路径见 [ci.md](ci.md)。

**策略**：自行安装 SDK / JDK；`reflex-capacitor` 只检查并报错，不代装。

---

## 1. 先检查

```bash
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64   # 按本机路径改
export ANDROID_HOME=/usr/lib/android-sdk             # 或 Android Studio 的 Sdk 目录
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"

reflex-capacitor check --android
reflex-capacitor check --android --device   # 还要 adb
```

必需项大致包括：

| 项 | 要求 |
|----|------|
| Node.js / npm / npx | 20+ 建议 |
| Reflex | 与 `reflex-capacitor` 同一 Python 环境 |
| JDK | **17+**（AGP 常用 21） |
| Android SDK | `ANDROID_HOME`，含 platform-tools、至少一个 `platforms/android-*`、`build-tools` |
| adb | 仅 `run` / `dev` 必需 |

---

## 2. 出包命令

```bash
reflex-capacitor init --platform android   # 首次
reflex-capacitor sync
reflex-capacitor build android --debug     # debug APK
reflex-capacitor build android             # release（需 keystore）
```

产物常见路径：

```text
capacitor/android/app/build/outputs/apk/debug/app-debug.apk
```

签名与 AAB → [publishing.md](publishing.md)。

---

## 3. 代理与下载慢

默认**不走代理**。需要时：

```bash
reflex-capacitor build android --debug --proxy http://127.0.0.1:7890
# 或
export REFLEX_CAPACITOR_PROXY=http://127.0.0.1:7890
```

说明 → [cli.md](cli.md)。

可选：用户级 Gradle 镜像（如阿里云）写在 `~/.gradle/init.gradle`，与本 CLI 无关；**不要**在工程里写死代理主机，以免别人机器默认走你的代理。

Cursor 等环境若把 `GRADLE_USER_HOME` 指到临时目录，首次会重新下发行包；可强制：

```bash
export GRADLE_USER_HOME="$HOME/.gradle"
```

---

## 4. 常见失败

| 现象 | 处理 |
|------|------|
| `check` 报缺 JDK / SDK | 按提示安装并设 `JAVA_HOME` / `ANDROID_HOME` |
| Gradle 超时下 wrapper | 拉长网络或加 `--proxy`；见 `gradle-wrapper.properties` 的 `networkTimeout` |
| 缺 platform 35 | `sdkmanager "platforms;android-35"`（版本以工程为准） |
| 真机连不上后端 | 后端 `0.0.0.0`、同 Wi‑Fi、防火墙放行；见 [debug.md](debug.md) |
| WebSocket 失败 | HTTP 后端需 `androidScheme: http`（插件在 `http://` 时自动处理） |

---

## 相关

- 快速上手 → [00-getting-started.md](00-getting-started.md)
- 打包原理 → [packaging.md](../design/packaging.md)
- 真机调试 → [debug.md](debug.md)
