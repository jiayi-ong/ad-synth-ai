import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GeneratedImage:
    url: str
    base64: str | None = None


class ImageGenProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedImage:
        """Generate an image from a prompt. Returns a GeneratedImage with a URL."""


class MockImageGenProvider(ImageGenProvider):
    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedImage:
        # Returns a deterministic placeholder — no API calls
        logger.info("MockImageGenProvider.generate() called (no real image generated)")
        return GeneratedImage(
            url="https://placehold.co/800x1000/1a1a24/7c6cf5?text=Ad+Preview",
        )


class VertexAIImagenProvider(ImageGenProvider):
    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedImage:
        from google import genai
        from google.genai import types
        from backend.core.config import settings

        client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_region,
        )
        response = client.models.generate_images(
            model=settings.imagen_model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="4:5",
                safety_filter_level="block_some",
            ),
        )
        image = response.generated_images[0]
        # Return base64 data URI
        import base64
        b64 = base64.b64encode(image.image.image_bytes).decode()
        data_url = f"data:image/png;base64,{b64}"
        return GeneratedImage(url=data_url, base64=b64)


def create_image_provider() -> ImageGenProvider:
    from backend.core.config import settings
    if settings.image_gen_provider == "vertexai":
        return VertexAIImagenProvider()
    return MockImageGenProvider()
