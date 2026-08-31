/**
 * reflex-capacitor bridge — stable JS API for Reflex rx.call_script handlers.
 * Requires capacitor.js + plugin.js bundles loaded first (see inject.py).
 */
(function () {
  "use strict";

  const Cap = typeof window !== "undefined" ? window.Capacitor : undefined;
  const Plugins = Cap && Cap.Plugins ? Cap.Plugins : {};
  const MAX_LOGS = 100;
  const MAX_NATIVE_EVENTS = 200;
  const logs = [];
  const nativeEvents = [];
  let listenersReady = false;
  let pushListenersReady = false;
  let backButtonMode = "emit";
  let lastRecording = null;
  let playbackAudio = null;
  let mediaRecorder = null;
  let mediaChunks = [];
  let mediaStream = null;
  let recordingStartedAt = 0;

  function capPlatform() {
    return Cap && Cap.getPlatform ? Cap.getPlatform() : "web";
  }

  function capIsNative() {
    return !!(Cap && Cap.isNativePlatform && Cap.isNativePlatform());
  }

  function capIsAndroid() {
    return capPlatform() === "android";
  }

  function capIsIos() {
    return capPlatform() === "ios";
  }

  function capIsWeb() {
    return capPlatform() === "web";
  }

  function capPlatformInfo() {
    const p = capPlatform();
    return {
      platform: p,
      isNative: capIsNative(),
      isAndroid: p === "android",
      isIos: p === "ios",
      isWeb: p === "web",
    };
  }

  /** Prefer uri/webPath over huge dataUrl in native WebViews (Android + iOS). */
  function preferCameraUriResult(saveGallery) {
    return capIsNative() || !!saveGallery;
  }

  function plugin(name) {
    if (Plugins[name]) return Plugins[name];
    console.warn("reflex-capacitor: Capacitor plugin not loaded:", name);
    return null;
  }

  function recordingPlayUrl(rec) {
    if (!rec) return "";
    if (rec.dataUrl) return rec.dataUrl;
    if (rec.playUrl) return rec.playUrl;
    return "";
  }

  function pickRecordingMimeType() {
    if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) {
      return "";
    }
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/aac",
      "audio/ogg;codecs=opus",
    ];
    for (let i = 0; i < candidates.length; i++) {
      if (MediaRecorder.isTypeSupported(candidates[i])) {
        return candidates[i];
      }
    }
    return "";
  }

  function stopMediaStream() {
    if (!mediaStream) return;
    const tracks = mediaStream.getTracks ? mediaStream.getTracks() : [];
    for (let i = 0; i < tracks.length; i++) {
      try {
        tracks[i].stop();
      } catch (_err) {
        /* ignore */
      }
    }
    mediaStream = null;
  }

  function blobToDataUrl(blob) {
    return new Promise(function (resolve, reject) {
      const reader = new FileReader();
      reader.onloadend = function () {
        resolve(typeof reader.result === "string" ? reader.result : "");
      };
      reader.onerror = function () {
        reject(reader.error || new Error("read_failed"));
      };
      reader.readAsDataURL(blob);
    });
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
        const message = String(err && err.message ? err.message : err);
        addLog("error", name, {
          phase: "error",
          args: payload,
          error: message,
          stack: err && err.stack ? err.stack : undefined,
        });
        return { ok: false, error: message };
      }
    };
  }

  function isUserCancel(err) {
    const msg = String(err && err.message ? err.message : err).toLowerCase();
    return msg.indexOf("cancel") >= 0;
  }

  function locationGranted(perm) {
    return (
      (perm && perm.location === "granted") ||
      (perm && perm.coarseLocation === "granted")
    );
  }

  async function ensureCameraPermission(Cam, saveGallery) {
    let perm = await Cam.checkPermissions();
    if (perm.camera !== "granted") {
      perm = await Cam.requestPermissions({ permissions: ["camera"] });
      if (perm.camera !== "granted") {
        return { ok: false, error: "permission_denied", permission: perm };
      }
    }
    if (saveGallery) {
      perm = await Cam.checkPermissions();
      if (perm.photos !== "granted") {
        perm = await Cam.requestPermissions({ permissions: ["photos"] });
        if (perm.photos !== "granted") {
          return { ok: false, error: "photos_permission_denied", permission: perm };
        }
      }
    }
    return { ok: true };
  }

  async function ensurePhotosPermission(Cam) {
    let perm = await Cam.checkPermissions();
    if (perm.photos !== "granted") {
      perm = await Cam.requestPermissions({ permissions: ["photos"] });
      if (perm.photos !== "granted") {
        return { ok: false, error: "permission_denied", permission: perm };
      }
    }
    return { ok: true };
  }

  function pushNativeEvent(type, detail) {
    const entry = {
      ts: new Date().toISOString(),
      type: type,
      detail: detail || {},
    };
    nativeEvents.push(entry);
    if (nativeEvents.length > MAX_NATIVE_EVENTS) {
      nativeEvents.shift();
    }
    addLog("info", "nativeEvent", entry);
  }

  function setupPushListeners() {
    if (pushListenersReady) {
      return { ok: true, already: true };
    }
    const PN = plugin("PushNotifications");
    if (!PN) {
      return { ok: false, error: "plugin_missing" };
    }
    PN.addListener("registration", function (token) {
      pushNativeEvent("pushRegistration", {
        value: token && token.value ? token.value : "",
      });
    });
    PN.addListener("registrationError", function (err) {
      pushNativeEvent("pushRegistrationError", {
        error: err && err.error ? String(err.error) : String(err),
      });
    });
    PN.addListener("pushNotificationReceived", function (notification) {
      const n = notification || {};
      pushNativeEvent("pushNotificationReceived", {
        id: n.id != null ? n.id : "",
        title: n.title || "",
        body: n.body || "",
        data: n.data || {},
      });
    });
    PN.addListener("pushNotificationActionPerformed", function (action) {
      const a = action || {};
      const n = a.notification || {};
      pushNativeEvent("pushNotificationActionPerformed", {
        actionId: a.actionId || "",
        notification: {
          id: n.id != null ? n.id : "",
          title: n.title || "",
          body: n.body || "",
          data: n.data || {},
        },
      });
    });
    pushListenersReady = true;
    return { ok: true };
  }

  async function setupNativeListeners({ backButton }) {
    if (listenersReady) {
      return { ok: true, already: true, backButton: backButtonMode };
    }
    backButtonMode = backButton || "emit";
    const AppPlugin = plugin("App");
    if (AppPlugin) {
      AppPlugin.addListener("appStateChange", function (state) {
        pushNativeEvent("appStateChange", { isActive: state.isActive });
      });
      if (capIsAndroid()) {
        AppPlugin.addListener("backButton", function () {
          pushNativeEvent("backButton", {});
          if (backButtonMode === "exit") {
            AppPlugin.exitApp();
            return;
          }
          if (backButtonMode === "history" && window.history && window.history.length > 1) {
            window.history.back();
          }
        });
      }
      AppPlugin.addListener("appUrlOpen", function (data) {
        pushNativeEvent("appUrlOpen", { url: data && data.url ? data.url : "" });
      });
      AppPlugin.addListener("pause", function () {
        pushNativeEvent("pause", {});
      });
      AppPlugin.addListener("resume", function () {
        pushNativeEvent("resume", {});
      });
    }
    const Keyboard = plugin("Keyboard");
    if (Keyboard) {
      Keyboard.addListener("keyboardWillShow", function (info) {
        pushNativeEvent("keyboardWillShow", {
          keyboardHeight: info && info.keyboardHeight != null ? info.keyboardHeight : 0,
        });
      });
      Keyboard.addListener("keyboardWillHide", function () {
        pushNativeEvent("keyboardWillHide", {});
      });
    }
    listenersReady = true;
    setupPushListeners();
    return { ok: true, backButton: backButtonMode, platform: capPlatform() };
  }

  function drainNativeEvents() {
    const events = nativeEvents.slice();
    nativeEvents.length = 0;
    return { ok: true, count: events.length, events: events };
  }

  const core = {
    isNative() {
      return capIsNative();
    },

    platform() {
      return capPlatform();
    },

    platformInfo() {
      return capPlatformInfo();
    },

    isAndroid() {
      return capIsAndroid();
    },

    isIos() {
      return capIsIos();
    },

    isWeb() {
      return capIsWeb();
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
      const permResult = await ensureCameraPermission(Cam, saveGallery);
      if (!permResult.ok) return permResult;
      const q = Math.max(1, Math.min(Number(quality) || 90, 100));
      const useUri = preferCameraUriResult(saveGallery);
      try {
        const photo = await Cam.getPhoto({
          quality: q,
          allowEditing: false,
          resultType: useUri ? "uri" : "dataUrl",
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
      } catch (err) {
        if (isUserCancel(err)) {
          return { ok: false, cancelled: true, error: "user_cancelled" };
        }
        return { ok: false, error: String(err && err.message ? err.message : err) };
      }
    },

    async pickImages({ limit, quality }) {
      const Cam = plugin("Camera");
      if (!Cam) return { ok: false, error: "plugin_missing" };
      const permResult = await ensurePhotosPermission(Cam);
      if (!permResult.ok) return permResult;
      try {
        const result = await Cam.pickImages({
          quality: Math.max(1, Math.min(Number(quality) || 90, 100)),
          limit: Math.max(1, Math.min(Number(limit) || 1, 10)),
        });
        const photos = (result.photos || []).map(function (p) {
          return { webPath: p.webPath || "", format: p.format || "" };
        });
        return { ok: true, count: photos.length, photos: photos };
      } catch (err) {
        if (isUserCancel(err)) {
          return { ok: false, cancelled: true, error: "user_cancelled", count: 0, photos: [] };
        }
        return { ok: false, error: String(err && err.message ? err.message : err) };
      }
    },

    async getCurrentPosition({ enableHighAccuracy, timeout }) {
      const G = plugin("Geolocation");
      if (!G) return { ok: false, error: "plugin_missing" };
      let perm = await G.checkPermissions();
      if (!locationGranted(perm)) {
        perm = await G.requestPermissions();
        if (!locationGranted(perm)) {
          return { ok: false, error: "permission_denied", permission: perm };
        }
      }
      const timeoutMs = Math.max(8000, Math.min(Number(timeout) || 30000, 120000));
      const attempts =
        enableHighAccuracy === true
          ? [
              { accurate: true, label: "gps", timeout: Math.min(timeoutMs, 45000) },
              { accurate: false, label: "network", timeout: Math.min(timeoutMs, 15000) },
            ]
          : [
              { accurate: false, label: "network", timeout: Math.min(timeoutMs, 15000) },
              { accurate: true, label: "gps", timeout: Math.min(timeoutMs, 45000) },
            ];
      let lastError = null;
      for (let i = 0; i < attempts.length; i++) {
        const attempt = attempts[i];
        try {
          const pos = await G.getCurrentPosition({
            enableHighAccuracy: attempt.accurate,
            timeout: attempt.timeout,
            maximumAge: 60000,
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
            timeout: attempt.timeout,
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

    async startRecording() {
      if (typeof MediaRecorder === "undefined") {
        return { ok: false, error: "device_cannot_record" };
      }
      if (
        !navigator.mediaDevices ||
        typeof navigator.mediaDevices.getUserMedia !== "function"
      ) {
        return { ok: false, error: "device_cannot_record" };
      }
      if (mediaRecorder && mediaRecorder.state === "recording") {
        return { ok: false, error: "ALREADY_RECORDING" };
      }
      try {
        stopMediaStream();
        mediaChunks = [];
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeType = pickRecordingMimeType();
        mediaRecorder = mimeType
          ? new MediaRecorder(mediaStream, { mimeType: mimeType })
          : new MediaRecorder(mediaStream);
        mediaRecorder.ondataavailable = function (event) {
          if (event.data && event.data.size > 0) {
            mediaChunks.push(event.data);
          }
        };
        recordingStartedAt = Date.now();
        mediaRecorder.start();
        return { ok: true, recording: true, mimeType: mediaRecorder.mimeType || mimeType || "" };
      } catch (err) {
        stopMediaStream();
        mediaRecorder = null;
        const name = err && err.name ? String(err.name) : "";
        const message = String(err && err.message ? err.message : err);
        if (
          name === "NotAllowedError" ||
          name === "PermissionDeniedError" ||
          /Permission|NotAllowed|Denied/i.test(message)
        ) {
          return {
            ok: false,
            error: "permission_denied",
            detail: name || message,
            hint: "Android needs RECORD_AUDIO + MODIFY_AUDIO_SETTINGS in the APK manifest; reinstall after sync.",
          };
        }
        return { ok: false, error: message, detail: name || undefined };
      }
    },

    async stopRecording() {
      if (!mediaRecorder || mediaRecorder.state === "inactive") {
        return { ok: false, error: "RECORDING_HAS_NOT_STARTED" };
      }
      try {
        const recorder = mediaRecorder;
        const blob = await new Promise(function (resolve, reject) {
          const onStop = function () {
            recorder.removeEventListener("stop", onStop);
            recorder.removeEventListener("error", onError);
            const type = recorder.mimeType || (mediaChunks[0] && mediaChunks[0].type) || "audio/webm";
            resolve(new Blob(mediaChunks, { type: type }));
          };
          const onError = function (event) {
            recorder.removeEventListener("stop", onStop);
            recorder.removeEventListener("error", onError);
            reject((event && event.error) || new Error("FAILED_TO_FETCH_RECORDING"));
          };
          recorder.addEventListener("stop", onStop);
          recorder.addEventListener("error", onError);
          recorder.stop();
        });
        stopMediaStream();
        mediaRecorder = null;
        mediaChunks = [];
        const msDuration = Math.max(0, Date.now() - (recordingStartedAt || Date.now()));
        recordingStartedAt = 0;
        if (!blob || !blob.size) {
          return { ok: false, error: "EMPTY_RECORDING", msDuration: msDuration };
        }
        const dataUrl = await blobToDataUrl(blob);
        const mimeType = blob.type || "audio/webm";
        lastRecording = {
          dataUrl: dataUrl,
          playUrl: dataUrl,
          mimeType: mimeType,
          msDuration: msDuration,
          path: "",
        };
        return {
          ok: true,
          recording: false,
          dataUrl: dataUrl,
          playUrl: dataUrl,
          mimeType: mimeType,
          path: "",
          msDuration: msDuration,
          hasAudio: !!dataUrl,
        };
      } catch (err) {
        stopMediaStream();
        mediaRecorder = null;
        mediaChunks = [];
        recordingStartedAt = 0;
        return { ok: false, error: String(err && err.message ? err.message : err) };
      }
    },

    async playRecording({ dataUrl, path }) {
      let url = dataUrl || "";
      if (!url && path && Cap && typeof Cap.convertFileSrc === "function") {
        url = Cap.convertFileSrc(path);
      }
      if (!url) {
        url = recordingPlayUrl(lastRecording);
      }
      if (!url) {
        return { ok: false, error: "no_recording" };
      }
      try {
        if (playbackAudio) {
          playbackAudio.pause();
          playbackAudio = null;
        }
        playbackAudio = new Audio(url);
        await playbackAudio.play();
        return { ok: true, playing: true };
      } catch (err) {
        return { ok: false, error: String(err && err.message ? err.message : err) };
      }
    },

    async stopPlayback() {
      if (playbackAudio) {
        playbackAudio.pause();
        playbackAudio.currentTime = 0;
        playbackAudio = null;
      }
      return { ok: true, playing: false };
    },

    async recordingStatus() {
      let status = "NONE";
      if (mediaRecorder) {
        if (mediaRecorder.state === "recording") status = "RECORDING";
        else if (mediaRecorder.state === "paused") status = "PAUSED";
      }
      return {
        ok: true,
        status: status,
        hasLastRecording: !!(lastRecording && recordingPlayUrl(lastRecording)),
        lastMsDuration: lastRecording ? lastRecording.msDuration : 0,
        mediaRecorderSupported: typeof MediaRecorder !== "undefined",
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

    async pushRegister() {
      const PN = plugin("PushNotifications");
      if (!PN) {
        return { ok: false, error: "plugin_missing" };
      }
      setupPushListeners();
      let perm = await PN.checkPermissions();
      if (perm.receive !== "granted") {
        perm = await PN.requestPermissions();
        if (perm.receive !== "granted") {
          return { ok: false, error: "permission_denied", permission: perm };
        }
      }
      await PN.register();
      return { ok: true };
    },

    async pushCheckPermissions() {
      const PN = plugin("PushNotifications");
      if (!PN) {
        return { ok: false, error: "plugin_missing" };
      }
      const perm = await PN.checkPermissions();
      return { ok: true, permission: perm };
    },

    async pushRequestPermissions() {
      const PN = plugin("PushNotifications");
      if (!PN) {
        return { ok: false, error: "plugin_missing" };
      }
      const perm = await PN.requestPermissions();
      return {
        ok: perm.receive === "granted",
        permission: perm,
      };
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
        if (!photo.ok) return photo;
      } else if (src === "gallery") {
        const picked = await core.pickImages({ limit: 1, quality: q });
        if (!picked.ok) return picked;
        if (!picked.photos || !picked.photos.length) {
          return { ok: false, cancelled: true };
        }
        photo = { ok: true, webPath: picked.photos[0].webPath, format: picked.photos[0].format };
      } else {
        const Cam = plugin("Camera");
        if (!Cam) return { ok: false, error: "plugin_missing" };
        const permResult = await ensureCameraPermission(Cam, false);
        if (!permResult.ok) return permResult;
        try {
          const raw = await Cam.getPhoto({
            quality: q,
            resultType: preferCameraUriResult(false) ? "uri" : "dataUrl",
            source: "PROMPT",
          });
          photo = { ok: true, dataUrl: raw.dataUrl, webPath: raw.webPath, format: raw.format };
        } catch (err) {
          if (isUserCancel(err)) {
            return { ok: false, cancelled: true, error: "user_cancelled" };
          }
          return { ok: false, error: String(err && err.message ? err.message : err) };
        }
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
        "PushNotifications",
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
        isNative: capIsNative(),
        platform: capPlatform(),
        isAndroid: capIsAndroid(),
        isIos: capIsIos(),
        isWeb: capIsWeb(),
        capacitorCore: !!(Cap && Cap.isNativePlatform),
        pluginsLoaded: loaded,
        pluginsMissing: missing,
        logCount: logs.length,
        nativeListenerReady: listenersReady,
        pushListenerReady: pushListenersReady,
        nativeEventBuffer: nativeEvents.length,
        location: typeof window !== "undefined" && window.location ? window.location.href : "",
        userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
      };
    },

    setupNativeListeners: wrap("setupNativeListeners", setupNativeListeners),
    drainNativeEvents: wrap("drainNativeEvents", function () {
      return drainNativeEvents();
    }),
  };

  Object.keys(core).forEach(function (key) {
    if (
      key === "isNative" ||
      key === "platform" ||
      key === "platformInfo" ||
      key === "isAndroid" ||
      key === "isIos" ||
      key === "isWeb"
    ) {
      return;
    }
    bridge[key] = wrap(key, core[key]);
  });

  bridge.platformInfo = core.platformInfo;
  bridge.isAndroid = core.isAndroid;
  bridge.isIos = core.isIos;
  bridge.isWeb = core.isWeb;

  window.__REFLEX_CAPACITOR__ = bridge;
  addLog("info", "init", bridge.getDiagnostics());
})();
