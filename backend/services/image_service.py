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
        import base64
        b64 = base64.b64encode(image.image.image_bytes).decode()
        data_url = f"data:image/png;base64,{b64}"
        return GeneratedImage(url=data_url, base64=b64)


class GeminiImageProvider(ImageGenProvider):
    """
    Uses Gemini's native image generation via the google-genai SDK.
    Works locally with GOOGLE_API_KEY and on Cloud Run with Vertex AI credentials.

    Model: configurable via GEMINI_IMAGE_MODEL env var.
    Verify the current model ID at https://ai.google.dev/gemini-api/docs/image-generation
    Default: gemini-2.0-flash-exp-image-generation
    """

    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedImage:
        import base64
        from google import genai
        from google.genai import types
        from backend.core.config import settings

        if settings.google_genai_use_vertexai:
            client = genai.Client(
                vertexai=True,
                project=settings.gcp_project_id,
                location=settings.gcp_region,
            )
        else:
            client = genai.Client(api_key=settings.google_api_key)

        response = client.models.generate_content(
            model=settings.gemini_image_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None) is not None:
                b64 = base64.b64encode(part.inline_data.data).decode()
                mime = part.inline_data.mime_type or "image/png"
                data_url = f"data:{mime};base64,{b64}"
                return GeneratedImage(url=data_url, base64=b64)

        raise RuntimeError("GeminiImageProvider: no image part found in response")


class ShortAPIProvider(ImageGenProvider):
    """
    Aggregated image generation via ShortAPI.io.
    Supports Stable Diffusion, DALL-E, Flux, and other models through a single endpoint.
    Works anywhere with SHORTAPI_API_KEY set.
    """

    async def generate(self, prompt: str, reference_image_paths: list[str]) -> GeneratedImage:
        import httpx
        from backend.core.config import settings

        if not settings.shortapi_api_key:
            raise RuntimeError("SHORTAPI_API_KEY is not configured")

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.shortapi.io/v1/images/generate",
                headers={
                    "Authorization": f"Bearer {settings.shortapi_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "prompt": prompt,
                    "model": settings.shortapi_model,
                    "width": 800,
                    "height": 1000,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Handle common response envelope shapes across providers
        url = (
            data.get("url")
            or data.get("image_url")
            or (data.get("data") or [{}])[0].get("url")
        )
        if not url:
            raise RuntimeError(f"ShortAPIProvider: no URL in response: {data}")
        return GeneratedImage(url=url)


def create_image_provider() -> ImageGenProvider:
    from backend.core.config import settings
    match settings.image_gen_provider:
        case "vertexai":
            return VertexAIImagenProvider()
        case "gemini":
            return GeminiImageProvider()
        case "shortapi":
            return ShortAPIProvider()
        case _:
            return MockImageGenProvider()
