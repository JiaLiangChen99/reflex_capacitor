/**
 * Built-in mobile image editor (free-form crop, rotate, compress, watermark).
 * All processing runs in the WebView.
 */
(function () {
  "use strict";

  const CSS = `
.rc-editor-root{position:fixed;inset:0;z-index:2147483000;background:#0f1419;color:#e8eef4;
  display:flex;flex-direction:column;font-family:system-ui,sans-serif;touch-action:none;user-select:none}
.rc-editor-toolbar{display:flex;flex-wrap:wrap;gap:8px;padding:12px;padding-top:max(12px,env(safe-area-inset-top));
  background:#1a222c;border-bottom:1px solid #243040;align-items:center}
.rc-editor-toolbar button{padding:8px 12px;border:none;border-radius:8px;background:#243040;color:#e8eef4;
  font-size:14px;min-height:40px}
.rc-editor-toolbar button.active{background:#3d9a8b;color:#04120f;font-weight:600}
.rc-editor-toolbar button.primary{background:#3d9a8b;color:#04120f;font-weight:600}
.rc-editor-viewport{flex:1;position:relative;overflow:hidden;background:#000;touch-action:none}
.rc-editor-viewport canvas{position:absolute;inset:0;width:100%;height:100%;touch-action:none}
.rc-editor-overlay{position:absolute;inset:0;pointer-events:none}
.rc-editor-shade{position:absolute;background:rgba(0,0,0,.55);pointer-events:none}
.rc-editor-crop{position:absolute;border:2px solid #3d9a8b;box-shadow:0 0 0 9999px rgba(0,0,0,.55);
  pointer-events:auto;box-sizing:border-box;cursor:move}
.rc-editor-crop::before{content:"";position:absolute;inset:0;
  background:linear-gradient(rgba(255,255,255,.08) 1px,transparent 1px),
  linear-gradient(90deg,rgba(255,255,255,.08) 1px,transparent 1px);background-size:33.33% 33.33%}
.rc-editor-handle{position:absolute;width:22px;height:22px;background:#3d9a8b;border:2px solid #fff;
  border-radius:50%;transform:translate(-50%,-50%);pointer-events:auto;touch-action:none}
.rc-editor-hint{padding:8px 12px;font-size:12px;color:#8b9aab;text-align:center}
.rc-editor-crop-bar{display:flex;gap:6px;flex-wrap:wrap;padding:0 12px 8px}
.rc-editor-crop-bar button{font-size:12px;padding:6px 10px;border:none;border-radius:6px;background:#243040;color:#e8eef4}
.rc-editor-crop-bar button.active{background:#3d9a8b;color:#04120f}
`;

  const MIN_CROP = 48;
  const SCALE_MIN = 1;
  const SCALE_MAX = 3;

  function loadImage(src) {
    return new Promise(function (resolve, reject) {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = function () {
        resolve(img);
      };
      img.onerror = function () {
        reject(new Error("failed to load image"));
      };
      img.src = src;
    });
  }

  async function resolveSource(dataUrl, webPath) {
    if (dataUrl) return dataUrl;
    if (webPath) {
      const resp = await fetch(webPath);
      const blob = await resp.blob();
      return URL.createObjectURL(blob);
    }
    throw new Error("image_editor: no dataUrl or webPath");
  }

  function normalizeEditor(opts) {
    const o = opts || {};
    return {
      enableCrop: o.enableCrop !== false,
      enableRotate: o.enableRotate !== false,
      enableCompress: o.enableCompress !== false,
      enableWatermark: !!o.enableWatermark,
      watermarkText: String(o.watermarkText || ""),
      maxWidth: Math.max(320, Number(o.maxWidth) || 1920),
      quality: Math.max(0.1, Math.min(Number(o.quality) || 0.85, 1)),
      aspectRatio: o.aspectRatio == null ? null : Number(o.aspectRatio),
      saveToSandbox: !!o.saveToSandbox,
      sandboxPath: String(o.sandboxPath || "edited/photo.jpg"),
      saveToGallery: !!o.saveToGallery,
      returnDataUrl: o.returnDataUrl !== false,
    };
  }

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function getRotatedSize(iw, ih, rot) {
    const r = ((rot % 360) + 360) % 360;
    const rad = (r * Math.PI) / 180;
    const sin = Math.abs(Math.sin(rad));
    const cos = Math.abs(Math.cos(rad));
    return { rotW: iw * cos + ih * sin, rotH: iw * sin + ih * cos, rot: r };
  }

  function getDrawParams(img, view, vpW, vpH) {
    const iw = img.naturalWidth;
    const ih = img.naturalHeight;
    const rs = getRotatedSize(iw, ih, view.rotation);
    const fit = Math.min(vpW / rs.rotW, vpH / rs.rotH) * view.scale;
    const drawW = rs.rotW * fit;
    const drawH = rs.rotH * fit;
    return {
      iw: iw,
      ih: ih,
      rot: rs.rot,
      rotW: rs.rotW,
      rotH: rs.rotH,
      fit: fit,
      cx: vpW / 2 + view.panX,
      cy: vpH / 2 + view.panY,
      drawW: drawW,
      drawH: drawH,
    };
  }

  function screenToRotated(px, py, p) {
    let x = px - p.cx;
    let y = py - p.cy;
    const rad = (-p.rot * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    const rx = x * cos - y * sin;
    const ry = x * sin + y * cos;
    return { x: rx / p.fit + p.rotW / 2, y: ry / p.fit + p.rotH / 2 };
  }

  function cropViewportToRotated(crop, drawParams) {
    const pts = [
      screenToRotated(crop.x, crop.y, drawParams),
      screenToRotated(crop.x + crop.w, crop.y, drawParams),
      screenToRotated(crop.x + crop.w, crop.y + crop.h, drawParams),
      screenToRotated(crop.x, crop.y + crop.h, drawParams),
    ];
    let x1 = Math.min(pts[0].x, pts[1].x, pts[2].x, pts[3].x);
    let y1 = Math.min(pts[0].y, pts[1].y, pts[2].y, pts[3].y);
    let x2 = Math.max(pts[0].x, pts[1].x, pts[2].x, pts[3].x);
    let y2 = Math.max(pts[0].y, pts[1].y, pts[2].y, pts[3].y);
    x1 = clamp(x1, 0, drawParams.rotW);
    y1 = clamp(y1, 0, drawParams.rotH);
    x2 = clamp(x2, 0, drawParams.rotW);
    y2 = clamp(y2, 0, drawParams.rotH);
    return {
      x: x1,
      y: y1,
      width: Math.max(1, x2 - x1),
      height: Math.max(1, y2 - y1),
    };
  }

  function renderRotatedCanvas(img, drawParams) {
    const work = document.createElement("canvas");
    work.width = Math.max(1, Math.floor(drawParams.rotW));
    work.height = Math.max(1, Math.floor(drawParams.rotH));
    const wctx = work.getContext("2d");
    const rad = (drawParams.rot * Math.PI) / 180;
    wctx.translate(drawParams.rotW / 2, drawParams.rotH / 2);
    wctx.rotate(rad);
    wctx.drawImage(img, -drawParams.iw / 2, -drawParams.ih / 2);
    return work;
  }

  function exportImage(img, view, crop, editor, vpW, vpH) {
    const dp = getDrawParams(img, view, vpW, vpH);
    const work = renderRotatedCanvas(img, dp);
    const srcCrop = editor.enableCrop
      ? cropViewportToRotated(crop, dp)
      : { x: 0, y: 0, width: dp.rotW, height: dp.rotH };

    const out = document.createElement("canvas");
    out.width = Math.max(1, Math.floor(srcCrop.width));
    out.height = Math.max(1, Math.floor(srcCrop.height));
    out.getContext("2d").drawImage(
      work,
      srcCrop.x,
      srcCrop.y,
      srcCrop.width,
      srcCrop.height,
      0,
      0,
      out.width,
      out.height
    );

    let fw = out.width;
    let fh = out.height;
    if (editor.enableCompress && editor.maxWidth > 0 && fw > editor.maxWidth) {
      fh = Math.round((fh * editor.maxWidth) / fw);
      fw = editor.maxWidth;
    }
    const finalCanvas = document.createElement("canvas");
    finalCanvas.width = fw;
    finalCanvas.height = fh;
    const fctx = finalCanvas.getContext("2d");
    fctx.drawImage(out, 0, 0, fw, fh);

    if (editor.enableWatermark && editor.watermarkText) {
      const pad = Math.max(8, Math.floor(fw * 0.02));
      const fontSize = Math.max(12, Math.floor(fw * 0.035));
      fctx.font = "600 " + fontSize + "px system-ui,sans-serif";
      fctx.fillStyle = "rgba(255,255,255,0.85)";
      fctx.strokeStyle = "rgba(0,0,0,0.45)";
      fctx.lineWidth = 2;
      const text = editor.watermarkText;
      const tw = fctx.measureText(text).width;
      const tx = fw - tw - pad;
      const ty = fh - pad;
      fctx.strokeText(text, tx, ty);
      fctx.fillText(text, tx, ty);
    }

    const quality = editor.enableCompress ? editor.quality : 0.92;
    return {
      dataUrl: finalCanvas.toDataURL("image/jpeg", quality),
      width: fw,
      height: fh,
      format: "jpeg",
      rotation: dp.rot,
      crop: srcCrop,
    };
  }

  function defaultCrop(vpW, vpH) {
    const w = vpW * 0.75;
    const h = vpH * 0.55;
    return { x: (vpW - w) / 2, y: (vpH - h) / 2, w: w, h: h };
  }

  function openEditor(_ref) {
    const dataUrl = _ref.dataUrl;
    const webPath = _ref.webPath;
    const editor = normalizeEditor(_ref.editor);

    return resolveSource(dataUrl, webPath).then(function (src) {
      return loadImage(src).then(function (img) {
        return new Promise(function (resolve, reject) {
          const view = { rotation: 0, scale: 1, panX: 0, panY: 0 };
          let crop = { x: 0, y: 0, w: 100, h: 100 };
          let lockAspect = editor.aspectRatio;
          let vpW = 0;
          let vpH = 0;

          const root = document.createElement("div");
          root.className = "rc-editor-root";
          const style = document.createElement("style");
          style.textContent = CSS;
          root.appendChild(style);

          const toolbar = document.createElement("div");
          toolbar.className = "rc-editor-toolbar";

          function btn(label, cls, fn) {
            const b = document.createElement("button");
            b.textContent = label;
            if (cls) b.className = cls;
            b.onclick = fn;
            return b;
          }

          const viewport = document.createElement("div");
          viewport.className = "rc-editor-viewport";
          const canvas = document.createElement("canvas");
          const overlay = document.createElement("div");
          overlay.className = "rc-editor-overlay";
          const cropEl = document.createElement("div");
          cropEl.className = "rc-editor-crop";
          overlay.appendChild(cropEl);

          const handles = {};
          ["nw", "n", "ne", "e", "se", "s", "sw", "w"].forEach(function (name) {
            const h = document.createElement("div");
            h.className = "rc-editor-handle";
            h.dataset.handle = name;
            cropEl.appendChild(h);
            handles[name] = h;
          });

          const hint = document.createElement("div");
          hint.className = "rc-editor-hint";
          hint.textContent = "双指捏合缩放图片 · 拖裁剪框角/边 · 单指拖空白处平移";

          function layoutHandles() {
            const pos = {
              nw: [0, 0],
              n: [0.5, 0],
              ne: [1, 0],
              e: [1, 0.5],
              se: [1, 1],
              s: [0.5, 1],
              sw: [0, 1],
              w: [0, 0.5],
            };
            Object.keys(handles).forEach(function (name) {
              const p = pos[name];
              handles[name].style.left = p[0] * 100 + "%";
              handles[name].style.top = p[1] * 100 + "%";
            });
          }

          function redrawCanvas() {
            if (!vpW || !vpH) return;
            const ctx = canvas.getContext("2d");
            canvas.width = vpW;
            canvas.height = vpH;
            ctx.fillStyle = "#000";
            ctx.fillRect(0, 0, vpW, vpH);
            const dp = getDrawParams(img, view, vpW, vpH);
            ctx.save();
            ctx.translate(dp.cx, dp.cy);
            ctx.rotate((dp.rot * Math.PI) / 180);
            ctx.scale(dp.fit, dp.fit);
            ctx.drawImage(img, -dp.iw / 2, -dp.ih / 2);
            ctx.restore();
          }

          function syncCropEl() {
            cropEl.style.left = crop.x + "px";
            cropEl.style.top = crop.y + "px";
            cropEl.style.width = crop.w + "px";
            cropEl.style.height = crop.h + "px";
            cropEl.style.display = editor.enableCrop ? "block" : "none";
          }

          function resizeViewport() {
            vpW = viewport.clientWidth;
            vpH = viewport.clientHeight;
            if (crop.w <= 1) crop = defaultCrop(vpW, vpH);
            redrawCanvas();
            syncCropEl();
          }

          if (editor.enableRotate) {
            toolbar.appendChild(
              btn("↺ 90°", "", function () {
                view.rotation -= 90;
                redrawCanvas();
              })
            );
            toolbar.appendChild(
              btn("↻ 90°", "", function () {
                view.rotation += 90;
                redrawCanvas();
              })
            );
          }

          const cropBar = document.createElement("div");
          cropBar.className = "rc-editor-crop-bar";
          const ratioBtns = [];
          if (editor.enableCrop) {
            [
              ["自由", null],
              ["1:1", 1],
              ["4:3", 4 / 3],
              ["16:9", 16 / 9],
            ].forEach(function (pair) {
              const b = btn(pair[0], pair[1] === lockAspect ? "active" : "", function () {
                lockAspect = pair[1];
                ratioBtns.forEach(function (x) {
                  x.className = "";
                });
                b.className = "active";
              });
              ratioBtns.push(b);
              cropBar.appendChild(b);
            });
          }

          const zoomRange = document.createElement("input");
          zoomRange.type = "range";
          zoomRange.min = String(SCALE_MIN);
          zoomRange.max = String(SCALE_MAX);
          zoomRange.step = "0.05";
          zoomRange.value = "1";
          zoomRange.style.flex = "1";
          zoomRange.oninput = function () {
            view.scale = Number(zoomRange.value);
            redrawCanvas();
          };

          function syncZoomSlider() {
            zoomRange.value = String(view.scale);
          }

          function clampScale(s) {
            return clamp(s, SCALE_MIN, SCALE_MAX);
          }

          function pointerDistance(a, b) {
            return Math.hypot(b.x - a.x, b.y - a.y);
          }

          toolbar.appendChild(zoomRange);

          toolbar.appendChild(
            btn("取消", "", function () {
              root.remove();
              resolve({ ok: false, cancelled: true });
            })
          );
          toolbar.appendChild(
            btn("完成", "primary", async function () {
              try {
                const exported = exportImage(img, view, crop, editor, vpW, vpH);
                const result = {
                  ok: true,
                  cancelled: false,
                  width: exported.width,
                  height: exported.height,
                  format: exported.format,
                  rotation: exported.rotation,
                  localOnly: true,
                };
                if (editor.returnDataUrl) result.dataUrl = exported.dataUrl;
                const bridge = window.__REFLEX_CAPACITOR__;
                if (editor.saveToSandbox && bridge && bridge.fsWrite) {
                  const b64 = exported.dataUrl.split(",")[1];
                  await bridge.fsWrite({
                    path: editor.sandboxPath,
                    data: b64,
                    directory: "DATA",
                    encoding: "base64",
                  });
                  result.sandboxPath = editor.sandboxPath;
                }
                root.remove();
                resolve(result);
              } catch (e) {
                root.remove();
                reject(e);
              }
            })
          );

          root.appendChild(toolbar);
          if (editor.enableCrop) root.appendChild(cropBar);
          viewport.appendChild(canvas);
          viewport.appendChild(overlay);
          root.appendChild(viewport);
          root.appendChild(hint);
          document.body.appendChild(root);
          layoutHandles();
          requestAnimationFrame(resizeViewport);

          let dragMode = null;
          let startX = 0;
          let startY = 0;
          let startCrop = null;
          const canvasPointers = new Map();
          let isPinching = false;
          let pinchStartDist = 0;
          let pinchStartScale = 1;
          let pinchStartPanX = 0;
          let pinchStartPanY = 0;
          let pinchAnchorX = 0;
          let pinchAnchorY = 0;

          function beginPinch() {
            const pts = Array.from(canvasPointers.values());
            if (pts.length < 2) return;
            isPinching = true;
            dragMode = null;
            pinchStartDist = pointerDistance(pts[0], pts[1]);
            if (pinchStartDist < 8) pinchStartDist = 8;
            pinchStartScale = view.scale;
            pinchStartPanX = view.panX;
            pinchStartPanY = view.panY;
            pinchAnchorX = (pts[0].x + pts[1].x) / 2;
            pinchAnchorY = (pts[0].y + pts[1].y) / 2;
          }

          function updatePinch() {
            const pts = Array.from(canvasPointers.values());
            if (pts.length < 2) return;
            const dist = pointerDistance(pts[0], pts[1]);
            const newScale = clampScale(pinchStartScale * (dist / pinchStartDist));
            const ratio = newScale / pinchStartScale;
            view.scale = newScale;
            view.panX = pinchAnchorX - (pinchAnchorX - (vpW / 2 + pinchStartPanX)) * ratio - vpW / 2;
            view.panY = pinchAnchorY - (pinchAnchorY - (vpH / 2 + pinchStartPanY)) * ratio - vpH / 2;
            syncZoomSlider();
            redrawCanvas();
          }

          function applyAspectResize(nx, ny, nw, nh, handle) {
            if (!lockAspect || lockAspect <= 0) return { x: nx, y: ny, w: nw, h: nh };
            let w = nw;
            let h = w / lockAspect;
            if (handle === "n" || handle === "s") {
              h = nh;
              w = h * lockAspect;
            }
            if (handle === "nw" || handle === "sw" || handle === "w") {
              nx = startCrop.x + startCrop.w - w;
            }
            if (handle === "nw" || handle === "ne" || handle === "n") {
              ny = startCrop.y + startCrop.h - h;
            }
            return { x: nx, y: ny, w: w, h: h };
          }

          function onCropPointerDown(e) {
            if (isPinching) return;
            e.preventDefault();
            const target = e.target;
            dragMode = "move-crop";
            startX = e.clientX;
            startY = e.clientY;
            startCrop = { x: crop.x, y: crop.y, w: crop.w, h: crop.h };

            if (target.dataset && target.dataset.handle) {
              dragMode = "resize-" + target.dataset.handle;
            }
            const capEl = target.setPointerCapture ? target : cropEl;
            capEl.setPointerCapture(e.pointerId);
          }

          function onCropPointerMove(e) {
            if (isPinching || !dragMode) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;

            if (dragMode === "move-crop") {
              crop.x = clamp(startCrop.x + dx, 0, vpW - crop.w);
              crop.y = clamp(startCrop.y + dy, 0, vpH - crop.h);
              syncCropEl();
              return;
            }

            const handle = dragMode.replace("resize-", "");
            let nx = startCrop.x;
            let ny = startCrop.y;
            let nw = startCrop.w;
            let nh = startCrop.h;

            if (handle.indexOf("e") >= 0) nw = startCrop.w + dx;
            if (handle.indexOf("s") >= 0) nh = startCrop.h + dy;
            if (handle.indexOf("w") >= 0) {
              nx = startCrop.x + dx;
              nw = startCrop.w - dx;
            }
            if (handle.indexOf("n") >= 0) {
              ny = startCrop.y + dy;
              nh = startCrop.h - dy;
            }

            nw = Math.max(MIN_CROP, nw);
            nh = Math.max(MIN_CROP, nh);
            nx = clamp(nx, 0, vpW - MIN_CROP);
            ny = clamp(ny, 0, vpH - MIN_CROP);
            if (nx + nw > vpW) nw = vpW - nx;
            if (ny + nh > vpH) nh = vpH - ny;

            const adjusted = applyAspectResize(nx, ny, nw, nh, handle);
            crop.x = adjusted.x;
            crop.y = adjusted.y;
            crop.w = adjusted.w;
            crop.h = adjusted.h;
            syncCropEl();
          }

          function onCropPointerUp() {
            if (isPinching) return;
            dragMode = null;
          }

          function onCanvasPointerDown(e) {
            e.preventDefault();
            canvasPointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
            canvas.setPointerCapture(e.pointerId);
            if (canvasPointers.size === 2) {
              beginPinch();
              updatePinch();
            } else if (canvasPointers.size === 1 && !isPinching) {
              dragMode = "pan-image";
              startX = e.clientX;
              startY = e.clientY;
            }
          }

          function onCanvasPointerMove(e) {
            if (!canvasPointers.has(e.pointerId)) return;
            canvasPointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
            if (isPinching && canvasPointers.size >= 2) {
              updatePinch();
              return;
            }
            if (dragMode !== "pan-image" || canvasPointers.size !== 1) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            view.panX += dx;
            view.panY += dy;
            startX = e.clientX;
            startY = e.clientY;
            redrawCanvas();
          }

          function onCanvasPointerUp(e) {
            canvasPointers.delete(e.pointerId);
            if (canvasPointers.size < 2) isPinching = false;
            if (canvasPointers.size === 0) dragMode = null;
          }

          cropEl.addEventListener("pointerdown", onCropPointerDown);
          cropEl.addEventListener("pointermove", onCropPointerMove);
          cropEl.addEventListener("pointerup", onCropPointerUp);
          cropEl.addEventListener("pointercancel", onCropPointerUp);
          canvas.addEventListener("pointerdown", onCanvasPointerDown);
          canvas.addEventListener("pointermove", onCanvasPointerMove);
          canvas.addEventListener("pointerup", onCanvasPointerUp);
          canvas.addEventListener("pointercancel", onCanvasPointerUp);
        });
      });
    });
  }

  window.__REFLEX_CAPACITOR_IMAGE_EDITOR__ = { open: openEditor, normalizeEditor: normalizeEditor };
})();
