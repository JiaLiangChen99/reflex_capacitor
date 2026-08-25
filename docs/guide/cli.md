# CLI 参考

> 最后更新：2026-08-25

宿主依赖：**只检查、提示如何安装，不代装** Node / JDK / Android SDK / Xcode。  
项目内 `capacitor/` 的 `npm install` 仍由相关命令执行。

入口：`reflex-capacitor`（Click）。多数命令支持 `--app-dir`（默认 `.`）。

---

## 依赖检查

| 命令 | 作用 |
|------|------|
| `doctor` | 打印宿主依赖报告 |
| `check` | `doctor` 的别名 |

| 选项 | 作用 |
|------|------|
| `--android` | 检查 SDK、JDK 17+、platforms、build-tools、platform-tools |
| `--ios` | 检查 Xcode（非 macOS 必失败） |
| `--device` | 额外要求 `adb`（隐含需要 Android 项） |

必需项缺失时 **退出码非 0**。`init` / `build` / `run` / `dev` 在开跑前会跑同等检查并直接报错。

```bash
reflex-capacitor check --android
reflex-capacitor check --android --device
```

---

## 工程生命周期

| 命令 | 行为 | 预检 |
|------|------|------|
| `init --platform android\|ios` | scaffold `capacitor/`、`npm i`、`cap add` | Node + 对应平台 SDK |
| `sync` | `reflex export` → bridge → `npm i` → `cap sync` | Reflex + Node |
| `run android\|ios` | 默认先 sync，再 `cap run` | Android/iOS + **adb**（Android） |
| `dev android\|ios` | 导出/同步 + 本机后端 + 装包 | 同 `run` |
| `build android\|ios` | sync（可跳过）+ Gradle / `cap build ios` | Android/iOS（build **不**强制 adb） |
| `open android\|ios` | 打开 Android Studio / Xcode | 无强制预检 |

常用选项：

- `sync --skip-export`：复用已有 `www/`
- `run` / `build --skip-sync`：跳过 export+sync
- `build --debug` / 默认 `--release`；`--format apk|aab`
- `dev --live-reload`：UI 走 Vite；默认只热后端。详见 [dev-reload.md](dev-reload.md)
- 签名环境变量：见 [publishing.md](publishing.md)

---

## 代理（npm / Gradle）

默认：**不用代理**，并清掉子进程里的 `http_proxy` / `HTTPS_PROXY`，避免半残系统代理拖慢。

```bash
reflex-capacitor sync --proxy http://127.0.0.1:7890
reflex-capacitor build android --debug --proxy http://127.0.0.1:7890
export REFLEX_CAPACITOR_PROXY=http://127.0.0.1:7890   # 等价于每次传 --proxy
```

适用于：`init` / `sync` / `run` / `build` / `dev`。

---

## 失败时你会看到什么

缺必需宿主依赖时，错误形如：

```text
missing required host dependencies — install them yourself, then re-run
(this CLI does not install Node / JDK / Android SDK / Xcode):

  ✗ JDK 17+: not found …
      Install Temurin / OpenJDK 17 or 21 …

Full report:  reflex-capacitor doctor --android
```

请按提示自行安装后重跑 `check`，不要期待 CLI 自动 `apt`/`sdkmanager`。

---

## 相关

- 配置字段 → [configuration.md](configuration.md)
- 本机打 APK → [android-build.md](android-build.md)
- 打包流水线原理 → [packaging.md](../design/packaging.md)
