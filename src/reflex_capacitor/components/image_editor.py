"""Built-in image editor button — crop, rotate, compress, watermark on device."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import reflex as rx

from reflex_capacitor.bridge._script import call_bridge

ImageSource = Literal["prompt", "camera", "gallery"]


@dataclass(frozen=True, kw_only=True)
class ImageEditorOptions:
    """Options passed to the in-WebView image editor (all processing stays on device).

    Cropping uses a **free-form resizable box** by default (drag corners/edges).
    Set ``aspect_ratio`` (e.g. ``1.0``) to lock the crop box to that ratio in the UI.
    """

    enable_crop: bool = True
    enable_rotate: bool = True
    enable_compress: bool = True
    enable_watermark: bool = False
    watermark_text: str = ""
    max_width: int = 1920
    quality: int = 85
    aspect_ratio: float | None = None
    save_to_sandbox: bool = False
    sandbox_path: str = "edited/photo.jpg"
    return_data_url: bool = True

    def to_bridge(self) -> dict[str, Any]:
        """Serialize for ``window.__REFLEX_CAPACITOR_IMAGE_EDITOR__``."""
        q = self.quality / 100.0 if self.quality > 1 else self.quality
        return {
            "enableCrop": self.enable_crop,
            "enableRotate": self.enable_rotate,
            "enableCompress": self.enable_compress,
            "enableWatermark": self.enable_watermark,
            "watermarkText": self.watermark_text,
            "maxWidth": self.max_width,
            "quality": q,
            "aspectRatio": self.aspect_ratio,
            "saveToSandbox": self.save_to_sandbox,
            "sandboxPath": self.sandbox_path,
            "returnDataUrl": self.return_data_url,
        }


def image_editor_button(
    on_complete: Any,
    *,
    source: ImageSource = "prompt",
    options: ImageEditorOptions | None = None,
    label: str = "选择并编辑图片",
    **button_props: Any,
) -> rx.Component:
    """Button that opens the built-in image editor after camera/gallery/prompt pick.

    Processing (crop, rotate, compress, watermark) runs **only on the device**.
    The callback receives metadata and optionally ``dataUrl`` — omit large uploads
    by setting ``return_data_url=False`` and ``save_to_sandbox=True``.

    Example::

        from reflex_capacitor.components import ImageEditorOptions, image_editor_button

        image_editor_button(
            State.on_edited,
            source="camera",
            options=ImageEditorOptions(
                enable_watermark=True,
                watermark_text="© My App",
                save_to_sandbox=True,
                return_data_url=False,
            ),
            label="拍照并编辑",
        )
    """
    opts = (options or ImageEditorOptions()).to_bridge()
    return rx.button(
        label,
        on_click=call_bridge(
            "captureAndEdit",
            {"source": source, "editor": opts},
            callback=on_complete,
        ),
        **button_props,
    )
