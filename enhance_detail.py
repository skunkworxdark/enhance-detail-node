# 2024 skunkworxdark (https://github.com/skunkworxdark)
# Based on the `Enhance Detail` ComfyUI node from  https://github.com/spacepxl/ComfyUI-Image-Filters

import cv2
import numpy as np
from cv2.ximgproc import guidedFilter
from PIL import Image

from invokeai.invocation_api import (
    BaseInvocation,
    ImageField,
    ImageOutput,
    InputField,
    InvocationContext,
    WithBoard,
    WithMetadata,
    invocation,
)


@invocation(
    "enhance_detail",
    title="Enhance Detail",
    tags=["enhance", "detail", "image"],
    category="image",
    version="1.0.1",
)
class EnhanceDetailInvocation(BaseInvocation, WithMetadata, WithBoard):
    """Enhance Detail using guided filter"""

    # Inputs
    image: ImageField = InputField(description="The image to detail enhance")
    filter_radius: int = InputField(
        default=2,
        ge=1,
        le=64,
        description="radius of filter",
    )
    sigma: float = InputField(
        default=0.1,
        ge=0.01,
        le=100.0,
        description="sigma",
    )
    denoise: float = InputField(
        default=0.1,
        ge=0.0,
        le=10.0,
        description="denoise",
    )
    detail_multiplier: float = InputField(
        default=2.0,
        ge=0.0,
        le=100.0,
        description="detail multiplier",
    )

    def invoke(self, context: InvocationContext) -> ImageOutput:
        source = context.images.get_pil(self.image.image_name)
        source_rgb = source.convert(mode="RGB")

        # Check for zero filter radius and return original image
        if self.filter_radius == 0:
            return ImageOutput(image=self.image, width=source_rgb.width, height=source_rgb.height)

        # Convert to NumPy array 0..1
        np_img = np.array(source_rgb).astype(np.float32) / 255

        # Apply bilateral filtering for denoising (if denoise > 0.0)
        rad = self.filter_radius * 2 + 1
        denoise = self.denoise / 10
        imgB = cv2.bilateralFilter(np_img, rad, denoise, rad).astype(np.float32) if denoise > 0.0 else np_img

        # Apply guided filtering
        sig = self.sigma / 10
        imgG = np.clip(guidedFilter(np_img, np_img, rad, sig), 0.001, 1).astype(np.float32)

        # Apply detail enhancement and covert back to 0..255
        details = (imgB / imgG - 1) * self.detail_multiplier + 1
        output_array = (np.clip(details * imgG - imgB + np_img, 0, 1) * 255).astype(np.uint8)

        # Output Image
        output_image = Image.fromarray(output_array)
        # reapply original mode and Alpha channel if needed
        if "A" in source.mode:
            output_image.putalpha(source.getchannel("A"))

        if not (output_image.mode == source.mode):
            output_image.convert(source.mode)

        image_dto = context.images.save(output_image)
        return ImageOutput.build(image_dto)
