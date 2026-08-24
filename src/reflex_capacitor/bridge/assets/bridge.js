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

    /** Longer vibration — easier to feel on Android than short impact ticks. */
    async hapticsVibrate({ duration }) {
      const H = plugin("Haptics");
      const ms = Math.max(10, Math.min(Number(duration) || 300, 5000));
      if (!H) {
        if (typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate(ms);
          return { ok: true, fallback: "web_vibrate", duration: ms };
        }
        return { ok: false, error: "haptics_unavailable" };
      }
      if (typeof H.vibrate === "function") {
        await H.vibrate({ duration: ms });
        return { ok: true, duration: ms };
      }
      await H.impact({ style: "HEAVY" });
      return { ok: true, fallback: "impact_only", duration: ms };
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

    async prefSet({ key, value }) {
      const P = plugin("Preferences");
      if (!P) return { ok: false, error: "plugin_missing" };
      await P.set({ key: key || "", value: String(value ?? "") });
      return { ok: true, key: key };
    },

    async prefGet({ key }) {
      const P = plugin("Preferences");
      if (!P) return { ok: false, error: "plugin_missing", value: "" };
      const result = await P.get({ key: key || "" });
      return { ok: true, key: key, value: result && result.value != null ? result.value : "" };
    },

    async takePhoto({ quality, saveToGallery }) {
      const Cam = plugin("Camera");
      if (!Cam) return { ok: false, error: "plugin_missing" };
      const saveGallery = !!saveToGallery;
      let perm = await Cam.checkPermissions();
      if (perm.camera !== "granted" || perm.photos !== "granted") {
        perm = await Cam.requestPermissions({ permissions: ["camera", "photos"] });
        if (perm.camera !== "granted") {
          return { ok: false, error: "permission_denied", permission: perm };
        }
        if (saveGallery && perm.photos !== "granted") {
          return { ok: false, error: "photos_permission_denied", permission: perm };
        }
      }
      // dataUrl: in-memory preview / upload; uri + saveToGallery: persist to system gallery
      const photo = await Cam.getPhoto({
        quality: Math.max(1, Math.min(Number(quality) || 90, 100)),
        allowEditing: false,
        resultType: saveGallery ? "uri" : "dataUrl",
        source: "CAMERA",
        saveToGallery: saveGallery,
      });
      return {
        ok: true,
        dataUrl: photo.dataUrl || "",
        webPath: photo.webPath || "",
        path: photo.path || "",
        format: photo.format || "",
        saved: !!photo.saved,
        saveToGallery: saveGallery,
      };
    },

    async pickImages({ limit, quality }) {
      const Cam = plugin("Camera");
      if (!Cam) return { ok: false, error: "plugin_missing" };
      let perm = await Cam.checkPermissions();
      if (perm.photos !== "granted") {
        perm = await Cam.requestPermissions({ permissions: ["photos"] });
        if (perm.photos !== "granted") {
          return { ok: false, error: "permission_denied", permission: perm };
        }
      }
      const result = await Cam.pickImages({
        quality: Math.max(1, Math.min(Number(quality) || 90, 100)),
        limit: Math.max(1, Math.min(Number(limit) || 1, 10)),
      });
      const photos = (result.photos || []).map(function (p) {
        return { webPath: p.webPath || "", format: p.format || "" };
      });
      return { ok: true, count: photos.length, photos: photos };
    },

    async getCurrentPosition({ enableHighAccuracy, timeout }) {
      const G = plugin("Geolocation");
      if (!G) return { ok: false, error: "plugin_missing" };
      let perm = await G.checkPermissions();
      if (perm.location !== "granted" && perm.coarseLocation !== "granted") {
        perm = await G.requestPermissions();
        if (perm.location !== "granted" && perm.coarseLocation !== "granted") {
          return { ok: false, error: "permission_denied", permission: perm };
        }
      }
      const timeoutMs = Math.max(10000, Math.min(Number(timeout) || 45000, 120000));
      // Indoor / first fix: network (coarse) is much faster than GPS.
      const attempts =
        enableHighAccuracy === true
          ? [{ accurate: true, label: "gps" }, { accurate: false, label: "network" }]
          : [{ accurate: false, label: "network" }, { accurate: true, label: "gps" }];
      let lastError = null;
      for (let i = 0; i < attempts.length; i++) {
        const attempt = attempts[i];
        try {
          const pos = await G.getCurrentPosition({
            enableHighAccuracy: attempt.accurate,
            timeout: timeoutMs,
            maximumAge: 300000,
          });
          return {
            ok: true,
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            altitude: pos.coords.altitude,
            timestamp: pos.timestamp,
            source: attempt.label,
          };
        } catch (err) {
          lastError = err;
          addLog("warn", "getCurrentPosition", {
            attempt: attempt.label,
            timeout: timeoutMs,
            error: String(err),
          });
        }
      }
      return {
        ok: false,
        error: "location_timeout",
        message: lastError ? String(lastError) : "unknown",
        hint:
          "已授权但仍超时：请确认系统「定位/GPS」已开启；室内先试网络定位，或到窗边/室外再试。",
        timeout: timeoutMs,
      };
    },

    async keyboardShow() {
      const K = plugin("Keyboard");
      if (!K) return { ok: false, error: "plugin_missing" };
      await K.show();
      return { ok: true };
    },

    async keyboardHide() {
      const K = plugin("Keyboard");
      if (!K) return { ok: false, error: "plugin_missing" };
      await K.hide();
      return { ok: true };
    },

    async browserOpen({ url }) {
      const B = plugin("Browser");
      if (!B) {
        if (typeof window !== "undefined" && url) {
          window.open(url, "_blank");
          return { ok: true, fallback: "window_open" };
        }
        return { ok: false, error: "browser_unavailable" };
      }
      await B.open({ url: url || "about:blank" });
      return { ok: true };
    },

    async fsWrite({ path, data, directory, encoding }) {
      const FS = plugin("Filesystem");
      if (!FS) return { ok: false, error: "plugin_missing" };
      await FS.writeFile({
        path: path || "reflex-capacitor.txt",
        data: data || "",
        directory: directory || "DATA",
        encoding: encoding || "utf8",
      });
      return { ok: true, path: path, directory: directory || "DATA" };
    },

    async fsRead({ path, directory }) {
      const FS = plugin("Filesystem");
      if (!FS) return { ok: false, error: "plugin_missing" };
      const result = await FS.readFile({
        path: path || "reflex-capacitor.txt",
        directory: directory || "DATA",
        encoding: "utf8",
      });
      return {
        ok: true,
        path: path,
        data: result.data != null ? result.data : "",
        directory: directory || "DATA",
      };
    },

    async invoke({ plugin: pluginName, method, args }) {
      const P = Plugins[pluginName];
      if (!P || typeof P[method] !== "function") {
        return { ok: false, error: "invoke_not_found", plugin: pluginName, method: method };
      }
      const result = await P[method](args || {});
      return { ok: true, result: result };
    },

    async editImage({ dataUrl, webPath, editor }) {
      const ed = window.__REFLEX_CAPACITOR_IMAGE_EDITOR__;
      if (!ed) return { ok: false, error: "image_editor_not_loaded" };
      return ed.open({ dataUrl: dataUrl, webPath: webPath, editor: editor || {} });
    },

    async captureAndEdit({ source, editor }) {
      const ed = window.__REFLEX_CAPACITOR_IMAGE_EDITOR__;
      if (!ed) return { ok: false, error: "image_editor_not_loaded" };
      const src = source || "prompt";
      const edOpts = editor || {};
      const q = Math.round((Number(edOpts.quality) || 0.85) * 100);
      let photo = null;
      if (src === "camera") {
        photo = await core.takePhoto({ quality: q, saveToGallery: false });
        if (!photo.ok && photo.error) return photo;
      } else if (src === "gallery") {
        const picked = await core.pickImages({ limit: 1, quality: q });
        if (!picked.photos || !picked.photos.length) {
          return { ok: false, cancelled: true };
        }
        photo = { ok: true, webPath: picked.photos[0].webPath, format: picked.photos[0].format };
      } else {
        const Cam = plugin("Camera");
        if (!Cam) return { ok: false, error: "plugin_missing" };
        await Cam.requestPermissions({ permissions: ["camera", "photos"] });
        const raw = await Cam.getPhoto({
          quality: q,
          resultType: "dataUrl",
          source: "PROMPT",
        });
        photo = { ok: true, dataUrl: raw.dataUrl, webPath: raw.webPath, format: raw.format };
      }
      return ed.open({
        dataUrl: photo.dataUrl,
        webPath: photo.webPath,
        editor: edOpts,
      });
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
        "Preferences",
        "Camera",
        "Geolocation",
        "Keyboard",
        "Browser",
        "Filesystem",
      ];
      const loaded = expected.filter(function (name) {
        return !!Plugins[name];
      });
      const missing = expected.filter(function (name) {
        return !Plugins[name];
      });
      return {
        bridgeLoaded: true,
        bridgeVersion: 2,
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
