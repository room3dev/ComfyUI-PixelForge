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
    Combines resolution selection with advanced resizing options.
    """
    
    ASPECT_RATIOS = {
        "1:1": (1, 1),
        "3:2": (3, 2),
        "4:3": (4, 3),
        "16:9": (16, 9),
        "16:10": (16, 10),
    }
    
    MP_BASE = 1024 * 1024
    
    upscale_methods = ["nearest-exact", "bilinear", "area", "bicubic", "lanczos"]
    
    @classmethod
    def INPUT_TYPES(cls):
        # Build all possible resolutions
        all_resolutions = cls._build_all_resolutions()
        
        return {
            "required": {
                "image": ("IMAGE",),
                # Resolution Matrix parameters
                "aspect_ratio": (
                    list(cls.ASPECT_RATIOS.keys()),
                    {"default": "3:2"},
                ),
                "orientation": (
                    ["landscape", "portrait", "square"],
                    {"default": "landscape"},
                ),
                "divisible_by": (
                    [16, 32, 64],
                    {"default": 16},
                ),
                "max_megapixels": (
                    ["1 MP", "2 MP", "4 MP", "6 MP", "8 MP", "12 MP", "16 MP"],
                    {"default": "4 MP"},
                ),
                "resolution": (all_resolutions, {"default": "1024×1024"}),
                # KJ Resize v2 parameters
                "upscale_method": (cls.upscale_methods, {"default": "lanczos"}),
                "keep_proportion": (
                    ["stretch", "resize", "pad", "pad_edge", "crop"],
                    {"default": "stretch"}
                ),
                "pad_color": ("STRING", {"default": "0, 0, 0", "tooltip": "RGB color for padding (e.g., '0, 0, 0' for black)"}),
                "crop_position": (
                    ["center", "top", "bottom", "left", "right"],
                    {"default": "center"}
                ),
            },
            "optional": {
                "mask": ("MASK",),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    RETURN_TYPES = ("IMAGE", "INT", "INT", "MASK")
    RETURN_NAMES = ("image", "width", "height", "mask")
    FUNCTION = "resize"
    CATEGORY = "PixelForge"
    DESCRIPTION = """
Resizes images to selected resolution with advanced options.

Combines PixelForge resolution selection with KJNodes Resize v2 features.
"""

    @classmethod
    def _build_all_resolutions(cls):
        """Generate all possible resolutions across all aspect ratios and settings."""
        unique_resolutions = set()
        
        for aspect_name, (ratio_w, ratio_h) in cls.ASPECT_RATIOS.items():
            for div in [16, 32, 64]:
                for max_mp in [1, 2, 4, 6, 8, 12, 16]:
                    max_pixels = max_mp * cls.MP_BASE
                    k = div
                    
                    while True:
                        w = ratio_w * k
                        h = ratio_h * k
                        total = w * h
                        
                        if total > max_pixels:
                            break
                        
                        unique_resolutions.add(f"{w}×{h}")
                        unique_resolutions.add(f"{h}×{w}")
                        
                        k += div
        
        sorted_resolutions = sorted(
            unique_resolutions,
            key=lambda r: (
                int(r.split("×")[0]) * int(r.split("×")[1]),
                int(r.split("×")[0])
            )
        )
        
        return sorted_resolutions if sorted_resolutions else ["1024×1024"]

    def resize(self, image, aspect_ratio, orientation, divisible_by, max_megapixels, resolution, 
               upscale_method, keep_proportion, pad_color, crop_position, mask=None):
        
        from comfy.utils import ProgressBar
        
        B, H, W, C = image.shape
        
        # Initialize progress bar for large batches
        pbar = None
        if B >= 100:
            pbar = ProgressBar(B)
        
        # Parse target resolution from PixelForge parameters
        target_width, target_height = map(int, resolution.split("×"))
        
        # Apply orientation (handle square, portrait, landscape swapping)
        if orientation == "portrait" and target_width > target_height:
            target_width, target_height = target_height, target_width
        elif orientation == "landscape" and target_width < target_height:
            target_width, target_height = target_height, target_width
        # For square (1:1), no swapping needed
        
        # Parse pad color
        try:
            pad_rgb = [int(x.strip()) / 255.0 for x in pad_color.split(",")]
            if len(pad_rgb) != 3:
                pad_rgb = [0.0, 0.0, 0.0]
        except:
            pad_rgb = [0.0, 0.0, 0.0]
        
        # Initialize padding variables
        pad_left = pad_right = pad_top = pad_bottom = 0
        
        width = target_width
        height = target_height
        
        # Calculate new dimensions based on keep_proportion mode
        if keep_proportion in ["resize", "pad", "pad_edge"]:
            # Calculate dimensions to maintain aspect ratio of INPUT image
            ratio = min(target_width / W, target_height / H)
            new_width = round(W * ratio)
            new_height = round(H * ratio)
            
            # Calculate padding if needed
            if keep_proportion in ["pad", "pad_edge"]:
                if crop_position == "center":
                    pad_left = (target_width - new_width) // 2
                    pad_right = target_width - new_width - pad_left
                    pad_top = (target_height - new_height) // 2
                    pad_bottom = target_height - new_height - pad_top
                elif crop_position == "top":
                    pad_left = (target_width - new_width) // 2
                    pad_right = target_width - new_width - pad_left
                    pad_top = 0
                    pad_bottom = target_height - new_height
                elif crop_position == "bottom":
                    pad_left = (target_width - new_width) // 2
                    pad_right = target_width - new_width - pad_left
                    pad_top = target_height - new_height
                    pad_bottom = 0
                elif crop_position == "left":
                    pad_left = 0
                    pad_right = target_width - new_width
                    pad_top = (target_height - new_height) // 2
                    pad_bottom = target_height - new_height - pad_top
                elif crop_position == "right":
                    pad_left = target_width - new_width
                    pad_right = 0
                    pad_top = (target_height - new_height) // 2
                    pad_bottom = target_height - new_height - pad_top
            
            width = new_width
            height = new_height
        
        # Crop logic
        if keep_proportion == "crop":
            old_height = H
            old_width = W
            old_aspect = old_width / old_height
            new_aspect = target_width / target_height
            
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
            
            # After crop, resize to target
            width = target_width
            height = target_height
        
        
        # Process images with progress tracking for large batches
        if pbar is not None:
            # Process images one by one for progress tracking
            resized_images = []
            resized_masks = []
            
            for i in range(B):
                single_image = image[i:i+1]
                single_mask = mask[i:i+1] if mask is not None else None
                
                # Resize single image
                resized_single = common_upscale(
                    single_image.movedim(-1, 1),
                    width,
                    height,
                    upscale_method,
                    crop="disabled"
                ).movedim(1, -1)
                resized_images.append(resized_single)
                
                # Resize mask if present
                if single_mask is not None:
                    if upscale_method == "lanczos":
                        resized_single_mask = common_upscale(
                            single_mask.unsqueeze(1).repeat(1, 3, 1, 1),
                            width,
                            height,
                            upscale_method,
                            crop="disabled"
                        ).movedim(1, -1)[:, :, :, 0]
                    else:
                        resized_single_mask = common_upscale(
                            single_mask.unsqueeze(1),
                            width,
                            height,
                            upscale_method,
                            crop="disabled"
                        ).squeeze(1)
                    resized_masks.append(resized_single_mask)
                
                pbar.update(1)
            
            resized_image = torch.cat(resized_images, dim=0)
            resized_mask = torch.cat(resized_masks, dim=0) if resized_masks else None
        else:
            # Process entire batch at once for small batches
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
