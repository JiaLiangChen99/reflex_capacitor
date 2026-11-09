# Unreleased 审查报告（相对 v0.3.2）

> **审查基准**：Git tag `v0.3.2`（`pyproject.toml` 版本仍为 `0.3.2`）→ 当前 `main`（`196192f`）  
> **审查日期**：2026-11-09  
> **范围**：只读；对照 `CHANGELOG.md` 的 `[Unreleased]` 与 `git diff v0.3.2..HEAD`（34 文件，+1562 / −54 行）  
> **验证**：`pip install -e .` + `pytest tests/ -m "not device"` → **53 passed**，3 个 device 用例 deselect；`python -m build` _wheel 含 `bridge.js`（≈38KB）_

---

## 1. 执行摘要

自 v0.3.2 以来，`main` 上累积 **8 个提交**，主题集中在：**浏览器 dev 与 Cap 一致的 bridge 加载**、**内置录音/TTS**、**Android 麦克风与 audio focus**、**Cap 感知的 upload URL**、**默认插件集从 CORE 扩到 ALL**。实现与 CHANGELOG `[Unreleased]` **大体一致**；单元/集成测试覆盖较好，但 **真机 L3（TTS 抢焦点、录音、QQ 音乐场景）仍依赖人工**。

**发版建议**：建议发布 **`0.4.0`**（ MINOR bump 偏保守时可称「行为默认变更」：默认 `plugins`、更多 Manifest/npm 依赖、向 Android 工程写入生成的 `AudioFocusPlugin.java` 并改写 `MainActivity`）。若维护者坚持语义化仅 PATCH，可用 `0.3.3` 但须在 Release Notes 用粗体强调 **默认插件与 sync 副作用**。

**阻塞项**：无 CI/单测层面的硬阻塞；**软阻塞** = 至少一轮 `scripts/device-smoke.sh` + 真机验证录音/TTS/audio focus 后再发 PyPI。

---

## 2. Unreleased 功能/修复清单（CHANGELOG ↔ 代码核对）

| CHANGELOG 条目 | 代码中存在 | 证据/备注 |
|----------------|------------|-----------|
| `CapacitorPlugin.plugins` 默认为 `ALL_PLUGIN_IDS` | ✅ | `plugin.py` L84；`test_plugin.py` 断言默认 ALL |
| `get_upload_url` / `resolve_backend_base` | ✅ | 新模块 `urls.py`；`__init__.py` 导出；`test_urls.py` |
| 内置录音/播放（`mobile.start/stop/play_recording`） | ✅ | `bridge.js` MediaRecorder 段；`api.py`；demo UI |
| `reflex run` 经 Vite `public/` + document inject 加载 bridge | ✅ | `get_static_assets` + `pre_compile` + `inject_bridge_scripts_into_document`；`test_bridge_document_inject.py` |
| Android `MODIFY_AUDIO_SETTINGS` | ✅ | `plugins.py` `ensure_android_microphone_permission`；集成测 Manifest 含该权限 |
| `mobile.speak` / `stop_speak` + community TTS ^6.1.0 | ✅ | `CAPACITOR_PLUGIN_PACKAGES` + `PLUGIN_PACKAGE_VERSIONS`；`bridge.js` `TextToSpeech` 优先 |
| TTS audio focus：`AudioFocusPlugin` + 默认 `pause` | ✅ | `android_audio_focus.py` + `finalize_bridge`；`bridge.js` `withAudioFocus` |
| `USAGE_MEDIA` + `AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE` | ✅ | 生成 Java 源码与 `test_android_audio_focus.py` |
| speak 回调含 `audioFocus.granted` | ✅ | `bridge.js` `withAudioFocus` 合并 `out.audioFocus` |
| Proxy 单测 Gradle 端口 7892→7890 | ✅ | `tests/test_network_env.py` diff（`test_child_env_sets_proxy_and_gradle_opts`） |

### CHANGELOG 未写但实际入 diff 的改动

| 改动 | 说明 |
|------|------|
| Demo `demo/cloud_media.py` + lifespan 拉取 `/_upload` 样例 | commit `9045f9a`；演示 `get_upload_url`，**建议补入 CHANGELOG** |
| `inject.py` 对 `voice-recorder` 等内置插件 **跳过 vendor script 标签** | 与 `BUILTIN_BRIDGE_PLUGIN_IDS` 一致；`test_inject.py` 覆盖 |
| iOS `NSMicrophoneUsageDescription`（`voice-recorder`） | `ios_plist.py`；`test_ios_plist.py` |
| README / `docs/guide/*` 默认插件文档与配置示例更新 | 与默认 ALL 对齐 |
| Demo `demo.py` 录音/TTS/云端媒体标签页 | 维护者验收资产，非 PyPI 运行时依赖 |

### 可能夸大或需澄清之处

- **「typically pauses background music」**：依赖 OEM 与音乐 App 对 audio focus 的实现；QQ Music 专项修复已编码，**不能保证全部 App**。
- **「load bridge in browser」**：仅在 Reflex document 含标准 `jsx("head",{},` 时注入；无 head 则 noop（有单测）。
- **`voice-recorder`「enable … for mic permissions」**：默认 ALL 已含该 id，**新用户不必再手动添加**；缩 CORE 时才需记得加。

---

## 3. 按模块分组的主要改动

### 3.1 CLI（`cli.py`）

- **无文件级 diff**（v0.3.2 → main）。代理相关仅 **测试修正**，实现未变。

### 3.2 CapacitorPlugin（`plugin.py`）

| 能力 | 说明 |
|------|------|
| 默认 `plugins` | `CORE_PLUGIN_IDS` → **`ALL_PLUGIN_IDS`**（行为变更） |
| `get_static_assets` | 将 `bridge.js` / `image-editor.js` 复制到 `public/reflex-capacitor/` |
| `pre_compile` | 修改 document root，注入 script 标签 |
| `finalize_bridge` | 麦克风 + TTS queries + **`install_audio_focus_plugin`** |

### 3.3 bridge.js（`assets/bridge.js`，约 +410 行）

- **录音**：`getUserMedia` → `MediaRecorder`，`dataUrl` 回放，`recordingStatus`。
- **TTS**：Capacitor `TextToSpeech.speak` → 回退 `speechSynthesis`（带 voices 等待超时）。
- **Audio focus 封装**：`withAudioFocus` 调用本地 `AudioFocus` 插件，`speak` 默认 `focusMode === "pause"`。
- **风险提示**：录音 blob 以 data URL 形式保存在内存，长录音 **内存与 WebView 稳定性** 需真机关注。

### 3.4 bridge 注入（`inject.py`）

- `build_bridge_snippet` 仅对有 npm 包的插件生成 vendor `<script>`，避免 `voice-recorder` 虚假引用。

### 3.5 Android 权限 / AudioFocus

- **Manifest**：`RECORD_AUDIO` + **`MODIFY_AUDIO_SETTINGS`**（WebView mic 必要条件）。
- **TTS queries**：`android.intent.action.TTS_SERVICE`。
- **生成代码**：`finalize_bridge` 在 `text-to-speech` 启用时向 **`android/` 树写入 `AudioFocusPlugin.java` 并 patch `MainActivity`**（须在 `super.onCreate` 之前 `registerPlugin`）。**幂等**有单测；用户自定义 MainActivity 逻辑时仍有 **合并冲突** 风险。

### 3.6 TTS（Python `api.py` + npm）

- Python：`speak(..., audio_focus: pause|duck|none)`，`stop_speak`。
- npm：`@capacitor-community/text-to-speech@^6.1.0`（Cap 7 线）。

### 3.7 Upload URL（`urls.py`）

- 解析顺序：`REFLEX_CAPACITOR_DEV_BACKEND_URL` → `CapacitorPlugin.backend_url` → `config.api_url`。
- 解决 APK 内 `rx.get_upload_url` / handler 里 `Endpoint.UPLOAD.get_url()` 指向 localhost 的问题。

### 3.8 测试

| 区域 | 文件 |
|------|------|
| URL 助手 | `test_urls.py`（新建） |
| Audio focus 安装 | `test_android_audio_focus.py`（新建） |
| Document 注入 | `test_bridge_document_inject.py`（新建） |
| 默认插件 / TTS 版本 | `test_plugin.py` 扩展 |
| Manifest 麦克风 | `test_integration_scaffold.py` |
| 代理端口 | `test_network_env.py` |

**未覆盖**：端到端真机录音权限流程、TTS 与第三方音乐并发、iOS TTS/category。

### 3.9 文档

- `configuration.md`、`README.md`：**默认 ALL** 已更新。
- `02-native-bridge.md`、`permissions.md`、`debug.md` 等有 TTS/录音条目。
- **缺口**：`permissions.md` 页眉仍写「2026-08-25」；表格 **未单独列出 `voice-recorder` 行**（麦克风权限在集成测与 iOS plist 中已处理）。

---

## 4. 风险点与回归关注点

### 4.1 权限与平台

- **Android 录音**：须 Manifest 双权限 + 运行时授权；缺 `MODIFY_AUDIO_SETTINGS` 的历史项目需 **重新 `sync`/finalize**。
- **iOS 录音**：`NSMicrophoneUsageDescription` 仅在 `voice-recorder` ∈ plugins 时写入；App Store 审核依赖文案。
- **默认 ALL**：同步后 `package.json` 增加 camera/geo/TTS 等依赖，Manifest/Info.plist 补丁增多 → **权限面扩大**，升级用户应知情。

### 4.2 CORS / `backend_url`

- `get_upload_url` 与 baked `env.json` 一致性问题：Handler 必须用 `get_upload_url` 或 `resolve_backend_base`，否则服务端生成的 URL 仍可能错。
- Demo `rxconfig.py` **硬编码 LAN IP**（`192.168.1.56:8003`）仅适合维护者环境，**不应随包发布误导**（已在仓库 demo 中，非 wheel 内容）。

### 4.3 打包产物

- Wheel 经本地 build 验证含更新后 `bridge.js`。
- sdist `only-include` 未变；**sdist 不含本审查文件**（`docs/design/` 大多数不在 sdist 列表 — 符合现有 packaging 策略）。
- **Android 生成源码不入 PyPI wheel**，只在用户执行 sync/finalize 时落盘 — 升级库版本后需 **对用户 Cap 工程再 sync**。

### 4.4 PyPI / 版本号

- `pyproject.toml` 仍为 **0.3.2**，与 tag 一致，符合「本次不发版」。
- 发版时需：**升版本**、将 `[Unreleased]` 下移 dated 节、打 tag 触发 `publish-pypi.yml`。

### 4.5 平台差异

- **Audio focus 插件仅 Android**；iOS 靠 TTS `category: "playback"`（bridge.js），行为与 Android 不对等。
- **浏览器 `reflex run`**：无 Capacitor vendor 时 TTS 走 `speechSynthesis`；录音仍依赖浏览器 MediaRecorder（与真机不同）。

### 4.6 破坏性 / 迁移

- 从未显式设置 `plugins` 的项目，下一次 `post_build`/sync 将拉 **更多 npm 包** 并申请更多权限 → 建议在 Release Note 写：「若需原 CORE 体积，显式 `plugins=CORE_PLUGIN_IDS`」。
- 已 fork 过 `MainActivity` 的项目：audio focus 安装可能 **无法自动 register**（`find_main_activity` 找不到或非标准结构时需人工合并）。

---

## 5. CHANGELOG 一致性结论

| 维度 | 结论 |
|------|------|
| Features/Fixes 列表 | 与代码 **高度一致**，均可追溯到实现与测试 |
| 遗漏 | Demo 云端媒体 lifespan、document inject、内置插件 inject 行为、iOS 麦克风文案 |
| 夸大 | 「typically pauses」宜加 OEM 限定；browser 场景与 APK 能力不对等未说明 |

---

## 6. 发版建议

| 选项 | 理由 |
|------|------|
| **推荐 `0.4.0`** | 默认 `plugins` 变更、Android 工程生成文件、对外新 API（`get_upload_url`、录音/TTS）— 用户感知为「小特性版本」 |
| 备选 `0.3.3` | 若团队将默认扩展仅视为 PATCH 内文档化变更；**必须**附迁移说明 |

**不建议立即发版若**：未完成至少一次真机 smoke（录音 + TTS + 后台音乐）；或未更新 CHANGELOG 遗漏项。

---

## 7. 审查环境说明

- 审查在云代理 VM 执行；`pytest` 在非 device 标记下全绿。
- **未执行**：`adb` device smoke、Gradle 实机构建、PyPI 上传试跑。
- `demo/cloud_media.py` 依赖外网下载 CDN 样例 — CI/离线环境可能失败（demo 专用）。

---

## 8. 建议的下一步

1. **补全 CHANGELOG `[Unreleased]`**：demo 云端媒体、`inject` 内置插件、iOS 麦克风；审慎措辞 TTS audio focus 的 OEM 差异。
2. **真机验收**：在默认 ALL 配置下跑 `scripts/device-smoke.sh`，并手动测录音、TTS、`audio_focus=duck/none`、后台 QQ/网易云。
3. **决定版本号**（建议 `0.4.0`），更新 `pyproject.toml`，将 Unreleased 归档为 dated 节，打 `v0.4.0` tag 发 PyPI。
4. **升级指引**：README/Release Note 增加「从 0.3.2 升级请 `reflex-capacitor sync` 重建 Android、检查 MainActivity diff、按需改回 `CORE_PLUGIN_IDS`」。
5. **文档小修**：`permissions.md` 增加 `voice-recorder` 行并更新页眉日期；可选在 `docs/design/testing.md` 记录 TTS/audio focus 的手动验收清单。
