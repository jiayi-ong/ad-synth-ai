import base64
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

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
    async def generate(
        self,
        prompt: str,
        reference_image_paths: list[str],
        reference_image_url: str | None = None,
    ) -> GeneratedImage:
        """Generate an image from a prompt. reference_image_url enables img2img editing."""


class MockImageGenProvider(ImageGenProvider):
    async def generate(
        self,
        prompt: str,
        reference_image_paths: list[str],
        reference_image_url: str | None = None,
    ) -> GeneratedImage:
        logger.info("MockImageGenProvider.generate() called (no real image generated)")
        return GeneratedImage(url="https://placehold.co/800x1000/f5f5f5/e84b2f?text=Ad+Preview")


class VertexAIImagenProvider(ImageGenProvider):
    async def generate(
        self,
        prompt: str,
        reference_image_paths: list[str],
        reference_image_url: str | None = None,
    ) -> GeneratedImage:
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
    """
    Uses Gemini's native image generation via the google-genai SDK.
    Works locally with GOOGLE_API_KEY and on Cloud Run with Vertex AI credentials.

    Model: configurable via GEMINI_IMAGE_MODEL env var.
    Default: gemini-2.0-flash-exp-image-generation

    When reference_image_url is provided (img2img), the reference image is sent
    as an inline image part alongside the text prompt for guided editing.
    """

    async def generate(
        self,
        prompt: str,
        reference_image_paths: list[str],
        reference_image_url: str | None = None,
    ) -> GeneratedImage:
        import httpx
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

        # Build contents: optionally prepend reference image for img2img editing
        contents: list = []
        if reference_image_url:
            if reference_image_url.startswith("data:"):
                # Inline data URL — decode the base64 bytes directly
                header, b64_data = reference_image_url.split(",", 1)
                mime = header.split(":")[1].split(";")[0]
                img_bytes = base64.b64decode(b64_data)
            else:
                # Remote URL — fetch the image bytes
                async with httpx.AsyncClient(timeout=20) as http:
                    resp = await http.get(reference_image_url)
                    resp.raise_for_status()
                    img_bytes = resp.content
                    mime = resp.headers.get("content-type", "image/png").split(";")[0]
            contents.append(types.Part(inline_data=types.Blob(data=img_bytes, mime_type=mime)))
            contents.append(types.Part(text=prompt))
        else:
            contents = prompt

        response = client.models.generate_content(
            model=settings.gemini_image_model,
            contents=contents,
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
    Async job-based image generation via ShortAPI.ai.
    Flow: POST /job/create → poll GET /job/query?id={job_id} until status==2.
    Model switching: set SHORTAPI_MODEL to any ShortAPI model ID, e.g.:
      google/nano-banana-pro/text-to-image
      bytedance/seedream-5.0/text-to-image
    """

    _BASE = "https://api.shortapi.ai/api/v1"
    _POLL_INTERVAL_S = 3
    _POLL_MAX_RETRIES = 40  # 120 s total

    async def generate(
        self,
        prompt: str,
        reference_image_paths: list[str],
        reference_image_url: str | None = None,
    ) -> GeneratedImage:
        import asyncio
        import httpx
        from backend.core.config import settings

        if not settings.shortapi_api_key:
            raise RuntimeError("SHORTAPI_API_KEY is not configured")

        model = settings.shortapi_model
        aspect_ratio = settings.shortapi_aspect_ratio
        auth_header = {"Authorization": f"Bearer {settings.shortapi_api_key}"}

        logger.info(
            "ShortAPI create job model=%s aspect_ratio=%s prompt_len=%d prompt_preview=%r",
            model, aspect_ratio, len(prompt), prompt[:150],
        )

        async with httpx.AsyncClient(timeout=30) as client:
            # Step 1: create job
            resp = await client.post(
                f"{self._BASE}/job/create",
                headers={**auth_header, "Content-Type": "application/json"},
                json={"model": model, "args": {"prompt": prompt, "aspect_ratio": aspect_ratio}},
            )
            logger.info("ShortAPI create status=%d", resp.status_code)
            if not resp.is_success:
                logger.error("ShortAPI create error status=%d body=%r", resp.status_code, resp.text[:500])
            resp.raise_for_status()
            create_data = resp.json()

            if create_data.get("code") != 0:
                raise RuntimeError(f"ShortAPI job create failed: {create_data}")

            job_id = create_data["data"]["job_id"]
            logger.info("ShortAPI job created job_id=%s", job_id)

            # Step 2: poll until done
            for attempt in range(self._POLL_MAX_RETRIES):
                await asyncio.sleep(self._POLL_INTERVAL_S)
                resp = await client.get(
                    f"{self._BASE}/job/query",
                    params={"id": job_id},
                    headers=auth_header,
                )
                resp.raise_for_status()
                poll_data = resp.json()
                if poll_data.get("code") != 0:
                    raise RuntimeError(f"ShortAPI job query failed: {poll_data}")
                status = poll_data["data"].get("status")
                logger.debug("ShortAPI poll attempt=%d job_id=%s status=%s", attempt + 1, job_id, status)
                if status == 2:
                    url = poll_data["data"]["result"]["images"][0]["url"]
                    logger.info("ShortAPI success job_id=%s url_prefix=%r", job_id, url[:80])
                    return GeneratedImage(url=url)
                if status not in (0, 1):
                    raise RuntimeError(f"ShortAPI job failed status={status}: {poll_data}")

        raise RuntimeError(
            f"ShortAPI job timed out after {self._POLL_MAX_RETRIES * self._POLL_INTERVAL_S}s (job_id={job_id})"
        )


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
        "shortapi": ShortAPIProvider,
        "mock": MockImageGenProvider,
    }.get(settings.image_gen_provider, MockImageGenProvider)()


def create_video_provider() -> VideoGenProvider:
    return MockVideoGenProvider()
