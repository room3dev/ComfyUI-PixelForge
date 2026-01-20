# PixelForge Resolution Matrix

A ComfyUI custom node for selecting mathematically valid image resolutions.

## Features

- Aspect ratio selection (1:1, 3:2, 4:3, 16:9, 16:10)
- Orientation switch (landscape / portrait)
- Divisibility constraints (16 / 32 / 64)
- Max megapixel limit  
  - 1 MP = 1024 × 1024 = 1,048,576 pixels
- **Real-time filtered resolution dropdown** (New!)
  - Resolultions update instantly when parameters are changed.
- Outputs:
  - Width (px)
  - Height (px)
  - Aspect ratio (W/H)
  - Orientation
  - Total megapixels (float)

## Installation

Copy the folder into:

```
ComfyUI/custom_nodes/
```

Restart ComfyUI.

## Category

```
PixelForge
```

## License

MIT
