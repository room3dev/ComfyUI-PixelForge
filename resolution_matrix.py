import comfy.utils

class PixelForge:
    DESCRIPTION = "A ComfyUI node for selecting mathematically valid image resolutions filtered by aspect ratio, orientation, and megapixel limit."

    """
    PixelForge Resolution Matrix
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

    # --- cached inputs for filtered dropdown (ComfyUI pattern) ---
    _last_aspect = "3:2"
    _last_divisible = 16
    _last_max_mp = 4

    @classmethod
    def INPUT_TYPES(cls):
        resolutions = cls._build_resolution_list()

        return {
            "required": {
                "aspect_ratio": (
                    list(cls.ASPECT_RATIOS.keys()),
                    {"default": cls._last_aspect},
                ),
                "orientation": (
                    ["landscape", "portrait"],
                    {"default": "landscape"},
                ),
                "divisible_by": (
                    [16, 32, 64],
                    {"default": cls._last_divisible},
                ),
                "max_megapixels": (
                    ["1 MP", "2 MP", "4 MP", "6 MP", "8 MP", "12 MP", "16 MP"],
                    {"default": f"{cls._last_max_mp} MP"},
                ),
                "resolution": (resolutions,),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
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
    def _build_resolution_list(cls):
        ratio_w, ratio_h = cls.ASPECT_RATIOS[cls._last_aspect]
        max_pixels = cls._last_max_mp * cls.MP_BASE
        div = cls._last_divisible

        resolutions = []
        k = div

        while True:
            w = ratio_w * k
            h = ratio_h * k
            total = w * h

            if total > max_pixels:
                break

            mp = total / cls.MP_BASE
            resolutions.append(f"{w}×{h}")

            k += div

        if not resolutions:
            resolutions.append("INVALID")

        return resolutions

    def forge(
        self,
        aspect_ratio,
        orientation,
        divisible_by,
        max_megapixels,
        resolution,
    ):
        # ---- update cache for dynamic dropdown ----
        PixelForge._last_aspect = aspect_ratio
        PixelForge._last_divisible = divisible_by
        PixelForge._last_max_mp = int(max_megapixels.split()[0])

        ratio_w, ratio_h = self.ASPECT_RATIOS[aspect_ratio]

        width, height = map(int, resolution.split("×"))

        if orientation == "portrait":
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
    "PixelForge": "PixelForge · Resolution Matrix"
}
