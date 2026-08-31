# 安装与 PyPI

> 最后更新：2026-08-25 · 总索引 [README.md](../README.md)

本文说明 **如何安装本库**、需要哪些**宿主依赖**，以及维护者如何 **发布到 PyPI**。  
打 APK 的步骤见 [00-getting-started.md](00-getting-started.md) / [android-build.md](android-build.md)。

---

## 1. 安装 Python 包

需要 **Python ≥ 3.10**，建议使用虚拟环境。

```bash
# 已发布到 PyPI 时（目标用法）
pip install reflex-capacitor

# 本仓库开发 / 未发布时
pip install -e .
# 或带测试依赖：
pip install -e ".[dev]"
```

声明依赖（`pyproject.toml`）：

| 包 | 用途 |
|----|------|
| `reflex>=0.9` | 应用框架与 `export` |
| `click>=8.1` | CLI |

安装后应有命令：

```bash
reflex-capacitor --help
reflex-capacitor check
```

---

## 2. 宿主依赖（不随 pip 安装）

本包**不会**通过 pip 安装 Node、JDK、Android SDK、Xcode。请自行安装后用检查命令确认：

```bash
reflex-capacitor check                 # Reflex + Node/npm/npx
reflex-capacitor check --android       # + SDK + JDK 17+
reflex-capacitor check --android --device  # + adb
```

| 用途 | 需要 |
|------|------|
| 仅 `sync`（导出前端 + Cap 工程） | Reflex、Node.js 20+、npm/npx |
| `init` / `build` Android | 上表 + Android SDK + JDK 17+ |
| `run` / `dev` Android | 上表 + `adb` + 设备/模拟器 |
| iOS | macOS + Xcode |

策略说明（决策 D7）→ [plan.md](../design/plan.md) · 命令 → [cli.md](cli.md)

`init` / `sync` 仍会在 **`capacitor/` 目录**执行 `npm install`（Capacitor 与插件的**项目内**依赖，不是系统全局 SDK）。

---

## 3. 装完最小验证

```bash
# 在已有 Reflex 工程中配置 CapacitorPlugin 后：
reflex-capacitor check --android
reflex-capacitor init --platform android
reflex-capacitor sync
```

配置示例 → [configuration.md](configuration.md)。  
默认 `plugins=` 为 `ALL_PLUGIN_IDS`（仍**不含**推送；推送用 `PHASE5_PLUGIN_IDS`）。

---

## 4. 维护者：发布到 PyPI

当前版本见 `pyproject.toml` 的 `version`（与 [CHANGELOG.md](../../CHANGELOG.md) 对齐后再发）。

### 4.1 发布前检查清单

- [ ] `CHANGELOG.md` 写好本版本条目；`version` 已 bump
- [ ] `pytest tests/ -q`（含 `-m integration`）通过
- [ ] `reflex-capacitor check` 在干净说明与文档一致
- [ ] README 示例可复制（默认不含 `PHASE5` 推送）
- [ ] sdist/wheel 含 `bridge/assets`（随 `packages` 一并打入）
- [ ] 未把本机 IP、keystore、密码写进仓库

### 4.2 GitHub Actions 自动发布（推荐）

仓库已配置 [`.github/workflows/publish-pypi.yml`](../../.github/workflows/publish-pypi.yml)：**发布 GitHub Release 时**自动 build 并上传 PyPI。

#### 一次性配置

1. **PyPI 账号**  
   注册 https://pypi.org/account/register/

2. **创建 API Token**  
   https://pypi.org/manage/account/token/  
   - **首次上传**该包：Token scope 选 **Entire account**（上传成功后可在 PyPI 上改项目级 token）  
   - Token name 随意，例如 `reflex-capacitor-github`  
   - 复制 token（一般以 `pypi-` 开头，**只显示一次**）

3. **写入 GitHub Secret**  
   仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**  
   - Name: `PYPI_API_TOKEN`  
   - Value: 上一步的 token  

4. **（可选）TestPyPI 试发**  
   若要先试：在 TestPyPI 同样建 token，secret 名可另设；或本地 `twine upload --repository testpypi`（见 4.3）。

#### 每次发版

1. 改 `pyproject.toml` 里 `version`（当前 `0.3.2`）  
2. 更新 `CHANGELOG.md`，提交并 push  
3. GitHub → **Releases** → **Draft a new release**  
   - Tag：`v0.3.2`（**必须**与 `pyproject.toml` 的 version 一致，带 `v` 前缀）  
   - Title / 说明：粘贴 CHANGELOG 摘要  
   - 点 **Publish release**  
4. Actions 里看 **Publish to PyPI** workflow；成功后：

```bash
pip install reflex-capacitor==0.3.2
```

Workflow 会：跑 L1 集成测试 → `python -m build` → 校验 wheel 含 `bridge.js` / scaffold → 校验 tag 与 version → `pypi-publish`。

### 4.3 本地手动构建与上传

```bash
pip install build twine
python -m build
twine check dist/*
# 测试索引（可选）
twine upload --repository testpypi dist/*
# 正式（需 export TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-xxx）
twine upload dist/*
```

推荐用 API token，不要把密码写进脚本。

### 4.4 用户侧安装验证

```bash
pip install reflex-capacitor==<version>
reflex-capacitor check
python -c "from reflex_capacitor import CapacitorPlugin, mobile; print('ok')"
```

### 4.5 包内包含 / 不包含

| 包含（wheel） | 不包含 |
|---------------|--------|
| `CapacitorPlugin`、CLI、`mobile.*`、bridge JS、scaffold 模板 | Android SDK / JDK / Node |
| 权限补丁与文档（sdist 含 `docs/`） | FCM / APNs 服务端、`google-services.json` |
| | 用户的 `capacitor/android` 工程（由 `init` 生成） |

---

## 5. 推送到 GitHub 前（勿提交清单）

以下内容**只应留在本机**或 **GitHub Secrets**，不要进仓库：

| 类别 | 示例 | 本仓库处理 |
|------|------|------------|
| 虚拟环境 | `.venv/`、`venv/` | ✅ `.gitignore` |
| Capacitor 工程 | `capacitor/`（含 `node_modules`、APK、`local.properties`） | ✅ 整目录忽略 |
| 构建产物 | `dist/`、`build/`、`*.apk`、`*.aab` | ✅ 已忽略 |
| 密钥 / 签名 | `*.keystore`、`keystore.properties`、Play 证书 | ✅ 已忽略；用 CI Secrets |
| 推送配置 | `google-services.json`、`GoogleService-Info.plist` | ✅ 已忽略 |
| 环境变量文件 | `.env`、含 token 的本地脚本 | ✅ 已忽略 |
| PyPI / Android CI | `PYPI_API_TOKEN`、`REFLEX_BACKEND_URL`、keystore base64 | ✅ 只放 GitHub Secrets |
| 本机 LAN IP | 个人 `backend_url`、代理地址 | ⚠️ 见下 |

**注意 `rxconfig.py`**：demo 里的 `backend_url` 会进 Git。请用文档示例 IP（如 `192.168.1.56`）或占位符，**不要**写你真实内网地址。真机调试在本机改即可，不必 push。

推送前可自检：

```bash
git status
git diff
# 确认没有 capacitor/、.venv/、*.apk、.env、keystore
git grep -E 'pypi-|password\s*=|secret\s*=' -- ':!docs/' ':!.github/'
```

---

## 相关

- [00-getting-started.md](00-getting-started.md) · [cli.md](cli.md) · [android-build.md](android-build.md)
- [publishing.md](publishing.md)（**应用商店**签名，不是 PyPI）
- [plan.md](../design/plan.md)
