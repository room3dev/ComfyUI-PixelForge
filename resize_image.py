import torch
import math
from comfy.utils import common_upscale

try:
    import comfy.model_management as model_management
    COMFY_AVAILABLE = True
except ImportError:
    COMFY_AVAILABLE = False

MAX_RESOLUTION = 8192


class PixelForgeResizeImage:
    """
    PixelForge Resize Image
    Advanced image resizing with multiple keep proportion modes, padding, and cropping.
    """
    
    upscale_methods = ["nearest-exact", "bilinear", "area", "bicubic", "lanczos"]
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "width": ("INT", {"default": 512, "min": 0, "max": MAX_RESOLUTION, "step": 1}),
                "height": ("INT", {"default": 512, "min": 0, "max": MAX_RESOLUTION, "step": 1}),
                "upscale_method": (cls.upscale_methods, {"default": "lanczos"}),
                "keep_proportion": (
                    ["stretch", "resize", "pad", "pad_edge", "crop"],
                    {"default": "resize"}
                ),
                "pad_color": ("STRING", {"default": "0, 0, 0", "tooltip": "RGB color for padding (e.g., '0, 0, 0' for black)"}),
                "crop_position": (
                    ["center", "top", "bottom", "left", "right"],
                    {"default": "center"}
                ),
                "divisible_by": ("INT", {"default": 8, "min": 0, "max": 512, "step": 1}),
            },
            "optional": {
                "mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "MASK")
    RETURN_NAMES = ("image", "width", "height", "mask")
    FUNCTION = "resize"
    CATEGORY = "PixelForge"
    DESCRIPTION = """
Resizes images with advanced options for maintaining aspect ratio, padding, and cropping.

**Keep Proportion Modes:**
- **stretch**: Stretch to exact dimensions
- **resize**: Maintain aspect ratio, fit within dimensions
- **pad**: Resize and add padding to reach exact dimensions
- **pad_edge**: Pad using edge pixel extension
- **crop**: Crop to exact aspect ratio then resize

**Divisible By**: Ensures output dimensions are divisible by this value (useful for VAE/model requirements)
"""

    def resize(self, image, width, height, keep_proportion, upscale_method, divisible_by, pad_color, crop_position, mask=None):
        B, H, W, C = image.shape
        
        # Parse pad color
        try:
            pad_rgb = [int(x.strip()) / 255.0 for x in pad_color.split(",")]
            if len(pad_rgb) != 3:
                pad_rgb = [0.0, 0.0, 0.0]
        except:
            pad_rgb = [0.0, 0.0, 0.0]
        
        # Initialize padding variables
        pad_left = pad_right = pad_top = pad_bottom = 0
        
        # Calculate new dimensions based on keep_proportion mode
        if keep_proportion in ["resize", "pad", "pad_edge"]:
            # Calculate dimensions to maintain aspect ratio
            if width == 0 and height == 0:
                new_width = W
                new_height = H
            elif width == 0:
                ratio = height / H
                new_width = round(W * ratio)
                new_height = height
            elif height == 0:
                ratio = width / W
                new_width = width
                new_height = round(H * ratio)
            else:
                ratio = min(width / W, height / H)
                new_width = round(W * ratio)
                new_height = round(H * ratio)
            
            # Calculate padding if needed
            if keep_proportion in ["pad", "pad_edge"]:
                if crop_position == "center":
                    pad_left = (width - new_width) // 2
                    pad_right = width - new_width - pad_left
                    pad_top = (height - new_height) // 2
                    pad_bottom = height - new_height - pad_top
                elif crop_position == "top":
                    pad_left = (width - new_width) // 2
                    pad_right = width - new_width - pad_left
                    pad_top = 0
                    pad_bottom = height - new_height
                elif crop_position == "bottom":
                    pad_left = (width - new_width) // 2
                    pad_right = width - new_width - pad_left
                    pad_top = height - new_height
                    pad_bottom = 0
                elif crop_position == "left":
                    pad_left = 0
                    pad_right = width - new_width
                    pad_top = (height - new_height) // 2
                    pad_bottom = height - new_height - pad_top
                elif crop_position == "right":
                    pad_left = width - new_width
                    pad_right = 0
                    pad_top = (height - new_height) // 2
                    pad_bottom = height - new_height - pad_top
            
            width = new_width
            height = new_height
        else:
            # Stretch or crop mode
            if width == 0:
                width = W
            if height == 0:
                height = H
        
        # Apply divisibility constraint
        if divisible_by > 1:
            width = width - (width % divisible_by)
            height = height - (height % divisible_by)
        
        # Crop logic
        if keep_proportion == "crop":
            old_height = H
            old_width = W
            old_aspect = old_width / old_height
            new_aspect = width / height
            
            if old_aspect > new_aspect:
                crop_w = round(old_height * new_aspect)
                crop_h = old_height
            else:
                crop_w = old_width
                crop_h = round(old_width / new_aspect)
            
            # Calculate crop position
            if crop_position == "center":
                x = (old_width - crop_w) // 2
                y = (old_height - crop_h) // 2
            elif crop_position == "top":
                x = (old_width - crop_w) // 2
                y = 0
            elif crop_position == "bottom":
                x = (old_width - crop_w) // 2
                y = old_height - crop_h
            elif crop_position == "left":
                x = 0
                y = (old_height - crop_h) // 2
            elif crop_position == "right":
                x = old_width - crop_w
                y = (old_height - crop_h) // 2
            
            # Apply crop
            image = image[:, y:y+crop_h, x:x+crop_w, :]
            if mask is not None:
                mask = mask[:, y:y+crop_h, x:x+crop_w]
        
        # Resize image
        resized_image = common_upscale(
            image.movedim(-1, 1),
            width,
            height,
            upscale_method,
            crop="disabled"
        ).movedim(1, -1)
        
        # Resize mask if present
        resized_mask = None
        if mask is not None:
            if upscale_method == "lanczos":
                # Lanczos needs 3 channels
                resized_mask = common_upscale(
                    mask.unsqueeze(1).repeat(1, 3, 1, 1),
                    width,
                    height,
                    upscale_method,
                    crop="disabled"
                ).movedim(1, -1)[:, :, :, 0]
            else:
                resized_mask = common_upscale(
                    mask.unsqueeze(1),
                    width,
                    height,
                    upscale_method,
                    crop="disabled"
                ).squeeze(1)
        
        # Apply padding if needed
        if (keep_proportion in ["pad", "pad_edge"]) and (pad_left > 0 or pad_right > 0 or pad_top > 0 or pad_bottom > 0):
            # Adjust padding for divisibility
            padded_width = width + pad_left + pad_right
            padded_height = height + pad_top + pad_bottom
            
            if divisible_by > 1:
                width_remainder = padded_width % divisible_by
                height_remainder = padded_height % divisible_by
                if width_remainder > 0:
                    pad_right += divisible_by - width_remainder
                if height_remainder > 0:
                    pad_bottom += divisible_by - height_remainder
            
            # Create padded image
            if keep_proportion == "pad_edge":
                # Edge padding (replicate edge pixels)
                resized_image = torch.nn.functional.pad(
                    resized_image.permute(0, 3, 1, 2),
                    (pad_left, pad_right, pad_top, pad_bottom),
                    mode='replicate'
                ).permute(0, 2, 3, 1)
            else:
                # Color padding
                pad_tensor = torch.tensor(pad_rgb, device=resized_image.device, dtype=resized_image.dtype)
                padded_image = pad_tensor.view(1, 1, 1, 3).expand(
                    B,
                    height + pad_top + pad_bottom,
                    width + pad_left + pad_right,
                    C
                )
                padded_image[:, pad_top:pad_top+height, pad_left:pad_left+width, :] = resized_image
                resized_image = padded_image
            
            # Pad mask if present
            if resized_mask is not None:
                resized_mask = torch.nn.functional.pad(
                    resized_mask.unsqueeze(1),
                    (pad_left, pad_right, pad_top, pad_bottom),
                    mode='constant',
                    value=0.0
                ).squeeze(1)
        
        # Create default mask if none provided
        if resized_mask is None:
            resized_mask = torch.zeros(
                (B, resized_image.shape[1], resized_image.shape[2]),
                device=resized_image.device,
                dtype=torch.float32
            )
        
        final_width = resized_image.shape[2]
        final_height = resized_image.shape[1]
        
        return (resized_image, final_width, final_height, resized_mask)


NODE_CLASS_MAPPINGS = {
    "PixelForgeResizeImage": PixelForgeResizeImage
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PixelForgeResizeImage": "PixelForge · Resize Image"
}
