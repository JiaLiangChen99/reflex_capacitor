# 测试指南

> 最后更新：2026-08-25 · 总索引 [README.md](../README.md)

reflex-capacitor 采用分层测试：**L1 离线集成** → **L2 构建** → **L3 设备冒烟**。

## 快速命令

```bash
# 日常 / CI（不含真机）
uv run pytest tests/ -q

# 仅 L1 离线集成
uv run pytest tests/ -q -m integration

# L3 真机冒烟（需 adb + 已连接设备）
uv run pytest tests/test_device_smoke.py -q -m device

# 或直接跑 shell 脚本
chmod +x scripts/device-smoke.sh
./scripts/device-smoke.sh
```

CI（GitHub Actions）默认跑 `pytest tests/ -q`；无 adb 时 L3 用例自动 **skip**，不会失败。

---

## L1 — 离线集成 ✅

| 项 | 说明 |
|----|------|
| 文件 | `tests/test_integration_scaffold.py` |
| 需要 | Python + pytest only |
| 覆盖 | scaffold、`package.json`、bridge 注入、Manifest 权限、fake `node_modules` vendor 拷贝 |

无需 Node、adb、Android SDK。

---

## L2 — 构建集成

| 项 | 说明 |
|----|------|
| 位置 | GitHub Actions `android-apk.yml` |
| 需要 | Node、Java、Android SDK |
| 覆盖 | `reflex-capacitor sync` + Gradle 打 debug APK |

本地等价：

```bash
reflex-capacitor sync
cd capacitor/android && ./gradlew assembleDebug
```

APK 路径：`capacitor/android/app/build/outputs/apk/debug/app-debug.apk`

---

## L3 — 设备冒烟

### 环境（无桌面 Ubuntu VM + USB 真机）

1. 宿主机 USB 透传给 VM（VirtualBox / VMware USB 筛选器）。
2. VM 内安装 `adb`（Android platform-tools）。
3. 手机开启 **开发者选项 → USB 调试**，连接后：

```bash
adb devices
# 应显示一行 xxxxxxxx    device
```

4. 先完成至少一次 **L2 构建**（或让脚本自动 build）。

### 脚本：`scripts/device-smoke.sh`

步骤：

1. 检查 adb 设备（多设备时需 `ADB_SERIAL`）
2. 安装 debug APK（`-r` 覆盖安装）
3. 启动 `MainActivity`，等待 WebView 加载
4. 检查 logcat 是否出现 `[reflex-capacitor]`（bridge 已 init）
5. 可选：adb 触发深链，检查 `appUrlOpen`（需在 Manifest 配置 intent-filter）

**常用环境变量：**

| 变量 | 默认 | 说明 |
|------|------|------|
| `ADB_SERIAL` | 自动选唯一设备 | 多设备时指定 serial |
| `APP_ID` | 读 `capacitor.config.json` | 包名 |
| `SKIP_BUILD` | `0` | `1` = 使用已有 APK，不 sync/gradle |
| `FORCE_BUILD` | `0` | `1` = 强制重新 sync + assembleDebug |
| `SKIP_DEEP_LINK` | `0` | `1` = 跳过深链检查 |
| `REQUIRE_DEEP_LINK` | `0` | `1` = 无 appUrlOpen 则失败 |
| `DEEP_LINK_SCHEME` | `shell` | 与 Manifest intent-filter 一致 |
| `LAUNCH_WAIT_SEC` | `5` | 启动后等待 logcat 秒数 |

**示例：**

```bash
# 已有 APK，快速冒烟
SKIP_BUILD=1 ./scripts/device-smoke.sh

# 完整 rebuild + 安装
FORCE_BUILD=1 ./scripts/device-smoke.sh

# 深链必须通（需先按 deep-linking.md 改 Manifest）
REQUIRE_DEEP_LINK=1 SKIP_DEEP_LINK=0 ./scripts/device-smoke.sh
```

### pytest：`tests/test_device_smoke.py`

- 标记：`@pytest.mark.device`
- 无 adb 设备 → `pytest.skip`
- 默认 `SKIP_DEEP_LINK=1`（开发树常未配 intent-filter）
- 无 APK 且 `SKIP_BUILD=1` → skip 并提示先 build

---

## 手工回归（L3 补不全时）

在 demo App「原生」Tab 点一遍：通知、分享、深链展示、推送注册（需 FCM）。

LAN 后端：

```bash
reflex run --env prod --backend-only --backend-host 0.0.0.0 --backend-port 8001
reflex-capacitor dev android
```

---

## 故障排查

| 现象 | 处理 |
|------|------|
| `no adb device` | USB 调试、udev 规则、VM USB 透传 |
| `bridge not seen in logcat` | 重新 `reflex-capacitor sync`；确认在 Capacitor 壳内非浏览器 |
| 深链 WARN | 正常若未配 intent-filter；见 [deep-linking.md](deep-linking.md) |
| Gradle 失败 | `reflex-capacitor check --android`，检查 `ANDROID_HOME` / `JAVA_HOME` |
| 多设备 | `export ADB_SERIAL=$(adb devices \| awk 'NR==2{print $1}')` |

---

## 相关

- 分层说明 → 本文 L1–L3；决策与路线图 → [plan.md](plan.md)
- [deep-linking.md](deep-linking.md) · [ci.md](ci.md) · [cli.md](cli.md)（`doctor --android`）
- 文档总索引 → [README.md](../README.md)
