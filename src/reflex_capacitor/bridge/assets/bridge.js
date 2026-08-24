/**
 * reflex-capacitor bridge — stable JS API for Reflex rx.call_script handlers.
 * Requires capacitor.js + plugin.js bundles loaded first (see inject.py).
 */
(function () {
  "use strict";

  const Cap = typeof window !== "undefined" ? window.Capacitor : undefined;
  const Plugins = Cap && Cap.Plugins ? Cap.Plugins : {};
  const MAX_LOGS = 100;
  const logs = [];

  function plugin(name) {
    if (Plugins[name]) return Plugins[name];
    console.warn("reflex-capacitor: Capacitor plugin not loaded:", name);
    return null;
  }

  function addLog(level, method, detail) {
    const entry = {
      ts: new Date().toISOString(),
      level: level,
      method: method,
      detail: detail || {},
    };
    logs.unshift(entry);
    if (logs.length > MAX_LOGS) logs.length = MAX_LOGS;
    const prefix = "[reflex-capacitor]";
    if (level === "error") {
      console.error(prefix, method, detail);
    } else if (level === "warn") {
      console.warn(prefix, method, detail);
    } else {
      console.log(prefix, method, detail);
    }
  }

  function wrap(name, fn) {
    return async function wrapped(args) {
      const payload = args || {};
      addLog("info", name, { phase: "start", args: payload });
      try {
        const result = await fn(payload);
        addLog("info", name, { phase: "ok", args: payload, result: result });
        return result;
      } catch (err) {
        addLog("error", name, {
          phase: "error",
          args: payload,
          error: String(err),
          stack: err && err.stack ? err.stack : undefined,
        });
        throw err;
      }
    };
  }

  const core = {
    isNative() {
      return !!(Cap && Cap.isNativePlatform && Cap.isNativePlatform());
    },

    platform() {
      return Cap && Cap.getPlatform ? Cap.getPlatform() : "web";
    },

    async notify({ title, body }) {
      const LN = plugin("LocalNotifications");
      if (!LN) {
        if (typeof Notification !== "undefined" && Notification.permission === "granted") {
          new Notification(title || "", { body: body || "" });
        } else {
          addLog("warn", "notify", { fallback: "web Notification unavailable" });
        }
        return { ok: true, fallback: "web" };
      }
      let perm = await LN.checkPermissions();
      if (perm.display !== "granted") {
        perm = await LN.requestPermissions();
        if (perm.display !== "granted") {
          addLog("warn", "notify", { permission: perm });
          return { ok: false, error: "permission_denied", permission: perm };
        }
      }
      await LN.schedule({
        notifications: [
          {
            id: Math.floor(Date.now() % 2147483647),
            title: title || "",
            body: body || "",
          },
        ],
      });
      return { ok: true };
    },

    async toast({ text, duration }) {
      const T = plugin("Toast");
      if (!T) {
        addLog("warn", "toast", { fallback: "console", text: text });
        return { ok: true, fallback: "console" };
      }
      await T.show({
        text: text || "",
        duration: duration === "long" ? "long" : "short",
      });
      return { ok: true };
    },

    async hapticsImpact({ style }) {
      const H = plugin("Haptics");
      if (!H) return { ok: false, error: "plugin_missing" };
      await H.impact({ style: style || "MEDIUM" });
      return { ok: true };
    },

    async hapticsNotification({ type }) {
      const H = plugin("Haptics");
      if (!H) return { ok: false, error: "plugin_missing" };
      await H.notification({ type: type || "SUCCESS" });
      return { ok: true };
    },

    async share({ title, text, url, dialogTitle }) {
      const S = plugin("Share");
      if (!S) {
        if (navigator.share) {
          await navigator.share({ title, text, url });
          return { ok: true, fallback: "web_share" };
        }
        return { ok: false, error: "share_unavailable" };
      }
      await S.share({ title, text, url, dialogTitle });
      return { ok: true };
    },

    async clipboardWrite({ text }) {
      const C = plugin("Clipboard");
      if (!C) {
        if (navigator.clipboard) {
          await navigator.clipboard.writeText(text || "");
          return { ok: true, fallback: "web_clipboard" };
        }
        return { ok: false, error: "clipboard_unavailable" };
      }
      await C.write({ string: text || "" });
      return { ok: true };
    },

    async clipboardRead() {
      const C = plugin("Clipboard");
      if (!C) {
        if (navigator.clipboard) return { value: await navigator.clipboard.readText() };
        return { value: "", error: "clipboard_unavailable" };
      }
      const result = await C.read();
      return { value: result && result.value ? result.value : "" };
    },

    async statusBarSetStyle({ style }) {
      const SB = plugin("StatusBar");
      if (!SB) return { ok: false, error: "plugin_missing" };
      await SB.setStyle({ style: style || "DARK" });
      return { ok: true };
    },

    async statusBarHide() {
      const SB = plugin("StatusBar");
      if (!SB) return { ok: false, error: "plugin_missing" };
      await SB.hide();
      return { ok: true };
    },

    async statusBarShow() {
      const SB = plugin("StatusBar");
      if (!SB) return { ok: false, error: "plugin_missing" };
      await SB.show();
      return { ok: true };
    },

    async splashHide() {
      const SP = plugin("SplashScreen");
      if (!SP) return { ok: false, error: "plugin_missing" };
      await SP.hide();
      return { ok: true };
    },

    async deviceInfo() {
      const D = plugin("Device");
      if (!D) return { platform: core.platform(), isVirtual: false, fallback: true };
      return await D.getInfo();
    },

    async networkStatus() {
      const N = plugin("Network");
      if (!N) return { connected: navigator.onLine, connectionType: "unknown", fallback: true };
      return await N.getStatus();
    },

    async appExit() {
      const A = plugin("App");
      if (!A) return { ok: false, error: "plugin_missing" };
      await A.exitApp();
      return { ok: true };
    },
  };

  const bridge = {
    isNative: core.isNative,
    platform: core.platform,

    getLogs({ limit }) {
      const n = Math.max(1, Math.min(Number(limit) || 50, MAX_LOGS));
      return logs.slice(0, n);
    },

    clearLogs() {
      logs.length = 0;
      addLog("info", "clearLogs", { cleared: true });
      return { ok: true };
    },

    getDiagnostics() {
      const expected = [
        "LocalNotifications",
        "Clipboard",
        "Haptics",
        "Share",
        "StatusBar",
        "App",
        "SplashScreen",
        "Toast",
        "Device",
        "Network",
      ];
      const loaded = expected.filter(function (name) {
        return !!Plugins[name];
      });
      const missing = expected.filter(function (name) {
        return !Plugins[name];
      });
      return {
        bridgeLoaded: true,
        bridgeVersion: 1,
        isNative: core.isNative(),
        platform: core.platform(),
        capacitorCore: !!(Cap && Cap.isNativePlatform),
        pluginsLoaded: loaded,
        pluginsMissing: missing,
        logCount: logs.length,
        location: typeof window !== "undefined" && window.location ? window.location.href : "",
        userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
      };
    },
  };

  Object.keys(core).forEach(function (key) {
    if (key === "isNative" || key === "platform") return;
    bridge[key] = wrap(key, core[key]);
  });

  window.__REFLEX_CAPACITOR__ = bridge;
  addLog("info", "init", bridge.getDiagnostics());
})();
