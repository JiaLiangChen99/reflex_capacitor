# 真机开发 / 热重载

> Phase 3 · `reflex-capacitor dev`

在 Capacitor 壳内开发 Reflex 应用，有两种模式。

## 前置条件

1. 已执行 `reflex-capacitor init --platform android`
2. `rxconfig.py` 中配置了 `CapacitorPlugin` 且 `cors_allowed_origins` 包含 `*` 或 Capacitor origins
3. 手机与电脑在 **同一 Wi‑Fi**
4. Windows 防火墙放行 Reflex 后端端口（默认 **8000**）；热重载模式还需放行前端端口（默认 **3000**）

## 命令

```bash
# 默认：静态 UI 打进壳 + 仅后端热跑（推荐，与 CI APK 流程接近）
reflex-capacitor dev android

# 可选：UI 也从开发机 Vite 加载（热重载，需前端端口对 LAN 可达）
reflex-capacitor dev android --live-reload

# 指定 LAN IP（自动检测不准时）
reflex-capacitor dev android --lan-ip 192.168.1.56

# 跳过 export（仅改过后端逻辑、www 未变时）
reflex-capacitor dev android --skip-export
```

## 两种模式对比

| | 默认 `--no-live-reload` | `--live-reload` |
|---|-------------------------|-----------------|
| UI 来源 | 打包进 APK 的 `www/` | Capacitor `server.url` → Vite |
| Reflex 进程 | `reflex run --backend-only` | 完整 `reflex run` |
| 改 Python 后端 | 保存即生效 | 保存即生效 |
| 改 Reflex 前端 | 需重新 `dev`（会 re-export） | Vite HMR |
| 手机要求 | 能访问 LAN 后端端口 | 能访问 LAN 前端 + 后端端口 |

默认模式会：

1. 设置 `REFLEX_CAPACITOR_DEV_BACKEND_URL=http://<LAN>:<backend-port>`
2. `reflex export --frontend-only`（把 LAN 后端写进 `env.json`）
3. `npx cap sync`
4. 启动 `reflex run --backend-host 0.0.0.0 --backend-only`
5. `npx cap run android`

## 与 CI / 生产的关系

- **CI 打 APK**：仍用 GitHub Actions + `REFLEX_BACKEND_URL` secret，不跑 `dev`
- **`dev` 结束**：若用过 `--live-reload`，CLI 会清除 `capacitor.config.json` 里的 `server.url`；发布前请再执行一次 `reflex-capacitor sync`
- **生产**：HTTPS + WSS，`androidScheme: https`（插件在 `backend_url` 为 https 时自动设置）

## 反向原生事件（Phase 3.3）

App 启动时调用一次：

```python
mobile.setup_native_listeners(back_button="emit")
```

之后用 `mobile.poll_native_events(callback)` 取队列中的事件：

| type | 说明 |
|------|------|
| `appStateChange` | `{isActive: bool}` 前后台 |
| `pause` / `resume` | App 生命周期 |
| `backButton` | Android 返回键 |
| `keyboardWillShow` / `keyboardWillHide` | 软键盘 |
| `appUrlOpen` | 深链打开（预留） |

`back_button` 模式：

- `emit` — 仅入队，由 Reflex 处理（默认；注册后 Android 不会直接退出）
- `exit` — 直接退出 App
- `history` — `window.history.back()`

Demo 在「原生」Tab 提供 **刷新原生事件** 按钮。

## iOS

需 macOS + Xcode：

```bash
reflex-capacitor dev ios
```

本仓库 CI 暂只打 Android APK；iOS 见 [04-roadmap.md](04-roadmap.md) 3.4。

## 常见问题

**WebSocket timeout**

- HTTP 后端必须 `androidScheme: http`（插件已自动处理）
- 后端需 `--backend-host 0.0.0.0`，不能仅监听 `127.0.0.1`

**手机连不上开发机**

- 确认 IP：`ipconfig` / `ifconfig`
- 同网段、关闭 VPN
- 防火墙入站规则

**热重载 UI 空白**

- 前端 dev server 可能只监听 `127.0.0.1`；可先用默认模式（bundled www）
- 或查 Vite 是否允许 LAN 访问（依 Reflex 版本而定）
