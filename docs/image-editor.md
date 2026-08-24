# 内置图片编辑器

> Phase 3 · 设备本机处理，默认不上传云端

编辑器在 WebView 内运行（`image-editor.js`），支持拍照/选图后裁剪、旋转、压缩、文字水印。

## Python 用法

### 方式一：API 直接调用

```python
from reflex_capacitor import mobile

# 拍照 → 编辑 → 回调
mobile.capture_and_edit(
    State.on_edited,
    source="camera",  # "gallery" | "prompt" | "camera"
    editor=mobile.editor_options(
        enable_crop=True,
        enable_rotate=True,
        enable_compress=True,
        max_width=1920,
        quality=85,
        save_to_sandbox=True,
        sandbox_path="edited/photo.jpg",
        return_data_url=False,  # 推荐：不把大图回传后端
    ),
)

# 已有 dataUrl / webPath 时
mobile.edit_image(State.on_edited, web_path=path_from_camera)
```

### 方式二：组件按钮

```python
from reflex_capacitor.components import ImageEditorOptions, image_editor_button

image_editor_button(
    State.on_edited,
    source="camera",
    options=ImageEditorOptions(
        save_to_sandbox=True,
        return_data_url=False,
    ),
    label="拍照并编辑",
)
```

## 编辑器交互

| 操作 | 说明 |
|------|------|
| 拖四角/边 | 自由缩放裁剪框 |
| 双指捏合 | 缩放图片 |
| 单指拖空白 | 平移图片 |
| 比例按钮 | 自由 / 1:1 / 4:3 / 16:9 |
| 完成 | 导出 JPEG |

## `ImageEditorOptions` 主要字段

| 字段 | 默认 | 说明 |
|------|------|------|
| `enable_crop` | `True` | 是否显示裁剪 |
| `enable_rotate` | `True` | ±90° 旋转 |
| `enable_compress` | `True` | 按 `max_width` / `quality` 压缩 |
| `enable_watermark` | `False` | 文字水印 |
| `aspect_ratio` | `None` | `None`=自由裁剪；`1.0`=锁定 1:1 |
| `save_to_sandbox` | `False` | 写入 Capacitor 沙箱 |
| `return_data_url` | `True` | 是否在回调中带 base64 |

**推荐（remote 模式）**：`return_data_url=False` + `save_to_sandbox=True`，避免整图经 WebSocket 回传 Python 后端。

## 技术说明

- 注入路径：`sync` 时拷贝 `image-editor.js` 并在 `index.html` 加载
- Android 拍照默认返回 `webPath`（比巨大 `dataUrl` 更稳）
- 与 `take_photo()` 独立；`take_photo` 仅拍照，`capture_and_edit` 拍照后自动打开编辑器
