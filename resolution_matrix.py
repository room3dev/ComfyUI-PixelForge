import comfy.utils

class PixelForge:
    DESCRIPTION = "A ComfyUI node for selecting mathematically valid image resolutions filtered by aspect ratio, orientation, and megapixel limit."

    """
    PixelForge Resolution Selector
    A ComfyUI node for selecting mathematically valid resolutions
    filtered by aspect ratio, divisibility, orientation, and megapixel limit.
    """

    ASPECT_RATIOS = {
        "1:1": (1, 1),
        "3:2": (3, 2),
        "4:3": (4, 3),
        "16:9": (16, 9),
        "16:10": (16, 10),
    }

    MP_BASE = 1024 * 1024  # 1 MP = 1,048,576 pixels

    @classmethod
    def INPUT_TYPES(cls):
        # Generate ALL possible resolutions across all combinations
        # JavaScript will filter them dynamically based on user selections
        all_resolutions = cls._build_all_resolutions()

        return {
            "required": {
                "aspect_ratio": (
                    list(cls.ASPECT_RATIOS.keys()),
                    {"default": "1:1"},
                ),
                "orientation": (
                    ["landscape", "portrait", "square"],
                    {"default": "square"},
                ),
                "divisible_by": (
                    [16, 32, 64],
                    {"default": 16},
                ),
                "max_megapixels": (
                    ["1 MP", "2 MP", "4 MP", "6 MP", "8 MP", "12 MP", "16 MP"],
                    {"default": "1 MP"},
                ),
                "resolution": (all_resolutions, {"default": "1024×1024"}),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        # Accept any resolution string - JavaScript handles the filtering
        return True

    RETURN_TYPES = ("INT", "INT", "INT", "INT", "STRING", "FLOAT")
    RETURN_NAMES = (
        "width_px",
        "height_px",
        "ratio_w",
        "ratio_h",
        "orientation",
        "total_megapixels",
    )

    FUNCTION = "forge"
    CATEGORY = "PixelForge"

    # ------------------------------------------------------------

    @classmethod
    def _build_all_resolutions(cls):
        """Generate all possible resolutions across all aspect ratios and settings."""
        unique_resolutions = set()
        
        # Iterate through all combinations
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
                        
                        # Add both landscape and portrait orientations
                        unique_resolutions.add(f"{w}×{h}")
                        unique_resolutions.add(f"{h}×{w}")
                        
                        k += div
        
        # Sort by total pixels for better UX
        sorted_resolutions = sorted(
            unique_resolutions,
            key=lambda r: (
                int(r.split("×")[0]) * int(r.split("×")[1]),  # total pixels
                int(r.split("×")[0])  # width
            )
        )
        
        return sorted_resolutions if sorted_resolutions else ["1024×1024"]

    def forge(
        self,
        aspect_ratio,
        orientation,
        divisible_by,
        max_megapixels,
        resolution,
    ):
        ratio_w, ratio_h = self.ASPECT_RATIOS[aspect_ratio]

        width, height = map(int, resolution.split("×"))

        # Note: Orientation is already handled by the JavaScript selecting
        # the appropriate dimension order, but we keep this for safety
        if orientation == "portrait" and width > height:
            width, height = height, width
        elif orientation == "landscape" and width < height:
            width, height = height, width

        total_mp = (width * height) / self.MP_BASE

        pbar = comfy.utils.ProgressBar(1)
        pbar.update(1)

        return (
            width,
            height,
            ratio_w,
            ratio_h,
            orientation,
            round(total_mp, 4),
        )


NODE_CLASS_MAPPINGS = {
    "PixelForge": PixelForge
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PixelForge": "PixelForge · Resolution Selector"
}
