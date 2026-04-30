import base64
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Image types ───────────────────────────────────────────────────────────────

@dataclass
class GeneratedImage:
    url: str
    base64: str | None = None


@dataclass
class GeneratedVideo:
    url: str
    thumbnail_url: str | None = None


# ── Image providers ───────────────────────────────────────────────────────────

class ImageGenProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedImage:
        """Generate an image from a prompt. Returns a GeneratedImage with a URL."""


class MockImageGenProvider(ImageGenProvider):
    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedImage:
        logger.info("MockImageGenProvider.generate() called (no real image generated)")
        return GeneratedImage(url="https://placehold.co/800x1000/1a1a24/7c6cf5?text=Ad+Preview")


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
        b64 = base64.b64encode(image.image.image_bytes).decode()
        return GeneratedImage(url=f"data:image/png;base64,{b64}", base64=b64)


class GeminiImageProvider(ImageGenProvider):
    """Uses Google AI Studio (google_api_key) — usable in local dev without GCP."""

    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedImage:
        from google import genai
        from google.genai import types
        from backend.core.config import settings

        client = genai.Client(api_key=settings.google_api_key)
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
        b64 = base64.b64encode(image.image.image_bytes).decode()
        return GeneratedImage(url=f"data:image/png;base64,{b64}", base64=b64)


class ShortApiImageProvider(ImageGenProvider):
    """Scaffold for a third-party image generation API. Fill in endpoint and key."""

    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedImage:
        from backend.core.config import settings
        if not settings.shortapi_key:
            raise NotImplementedError(
                "ShortApiImageProvider requires SHORTAPI_KEY in .env. "
                "Update this provider implementation with the correct endpoint."
            )
        # TODO: implement with actual ShortAPI endpoint
        raise NotImplementedError("ShortApiImageProvider endpoint not yet configured.")


# ── Video providers (extensibility scaffold) ──────────────────────────────────

class VideoGenProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedVideo:
        """Generate a video from a prompt."""


class MockVideoGenProvider(VideoGenProvider):
    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedVideo:
        logger.info("MockVideoGenProvider.generate() called (no real video generated)")
        return GeneratedVideo(
            url="https://placehold.co/1920x1080/1a1a24/7c6cf5?text=Video+Preview",
            thumbnail_url="https://placehold.co/1920x1080/1a1a24/7c6cf5?text=Thumbnail",
        )


# ── Factory ───────────────────────────────────────────────────────────────────

def create_image_provider() -> ImageGenProvider:
    from backend.core.config import settings
    return {
        "vertexai": VertexAIImagenProvider,
        "gemini": GeminiImageProvider,
        "shortapi": ShortApiImageProvider,
        "mock": MockImageGenProvider,
    }.get(settings.image_gen_provider, MockImageGenProvider)()


def create_video_provider() -> VideoGenProvider:
    return MockVideoGenProvider()
