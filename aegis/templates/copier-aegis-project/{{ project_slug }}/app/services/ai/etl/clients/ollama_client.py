"""
Ollama API client for model discovery.

Fetches locally installed models from Ollama's REST API.
"""

from dataclasses import dataclass
from datetime import datetime

import httpx
from app.core.log import logger

# Default Ollama server URL for local development
OLLAMA_DEFAULT_URL = "http://localhost:11434"


@dataclass
class OllamaModel:
    """Model data from Ollama's /api/tags endpoint."""

    name: str  # Model name (e.g., "llama3.2:latest")
    size: int  # Model size in bytes
    digest: str  # Model digest/hash
    modified_at: datetime | None  # When model was last modified
    parameter_size: str | None = None  # e.g., "3B", "70B"
    quantization_level: str | None = None  # e.g., "Q4_0", "Q8_0"
    family: str | None = None  # Model family (e.g., "llama")

    @property
    def model_id(self) -> str:
        """Get model ID for catalog - keeps full name including tag.

        Ollama requires the exact model name with tag (e.g., 'qwen2.5:7b')
        to work correctly. Stripping the tag causes 404 errors.
        """
        return self.name

    @property
    def size_gb(self) -> float:
        """Get model size in gigabytes."""
        return self.size / (1024**3)


@dataclass
class OllamaRunningModel:
    """Model data from Ollama's /api/ps endpoint (running models)."""

    name: str  # Model name (e.g., "qwen2.5:14b")
    size: int  # Model size in bytes
    size_vram: int  # VRAM currently used by this model
    digest: str  # Model digest/hash
    expires_at: datetime | None  # When model will be unloaded if idle

    @property
    def size_vram_gb(self) -> float:
        """Get VRAM usage in gigabytes."""
        return self.size_vram / (1024**3)

    @property
    def is_warm(self) -> bool:
        """Check if model is warm (loaded and ready)."""
        return True  # If it's in /api/ps, it's warm


@dataclass
class OllamaServerStatus:
    """Status information from Ollama server."""

    available: bool  # Server is reachable
    version: str | None  # Server version if available
    running_models: list[OllamaRunningModel]  # Currently loaded models
    installed_models: list[OllamaModel]  # All installed models
    installed_models_count: int  # Total installed models
    total_vram_gb: float  # Total VRAM used by running models


class OllamaClient:
    """Client for fetching model data from local Ollama server."""

    TIMEOUT = 10.0  # Local server should respond quickly

    def __init__(self, base_url: str = OLLAMA_DEFAULT_URL) -> None:
        """Initialize the Ollama client.

        Args:
            base_url: Base URL for Ollama server (default: OLLAMA_DEFAULT_URL)
        """
        self.base_url = base_url.rstrip("/")

    async def fetch_models(self) -> list[OllamaModel]:
        """Fetch all installed models from Ollama.

        Returns:
            List of OllamaModel objects for locally installed models.

        Raises:
            httpx.HTTPError: If the request fails.
            httpx.ConnectError: If Ollama server is not running.
        """
        url = f"{self.base_url}/api/tags"

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
            raise

        models: list[OllamaModel] = []
        raw_models = data.get("models", [])
        logger.info(f"Fetched {len(raw_models)} models from Ollama")

        for raw in raw_models:
            try:
                model = self._parse_model(raw)
                models.append(model)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse Ollama model: {e}")
                continue

        return models

    async def is_available(self) -> bool:
        """Check if Ollama server is running and accessible.

        Returns:
            True if Ollama is available, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_running_models(self) -> list[OllamaRunningModel]:
        """Fetch currently running (loaded) models from Ollama.

        Uses the /api/ps endpoint to get models currently in memory.

        Returns:
            List of OllamaRunningModel objects for loaded models.

        Raises:
            httpx.HTTPError: If the request fails.
            httpx.ConnectError: If Ollama server is not running.
        """
        url = f"{self.base_url}/api/ps"

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
            raise

        models: list[OllamaRunningModel] = []
        raw_models = data.get("models", [])

        for raw in raw_models:
            try:
                model = self._parse_running_model(raw)
                models.append(model)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse Ollama running model: {e}")
                continue

        return models

    async def load_model(self, model_name: str, keep_alive: str = "10m") -> bool:
        """Load a model into VRAM (warm it up).

        Uses the /api/generate endpoint with an empty prompt to load
        the model into memory without generating text.

        Args:
            model_name: Name of the model to load (e.g., 'qwen2.5:7b')
            keep_alive: How long to keep the model in memory (default: '10m')

        Returns:
            True if model was loaded successfully, False otherwise.
        """
        url = f"{self.base_url}/api/generate"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    json={
                        "model": model_name,
                        "prompt": "",
                        "keep_alive": keep_alive,
                    },
                )
                response.raise_for_status()
                logger.info(f"Successfully loaded model: {model_name}")
                return True
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading model {model_name}: {e}")
            return False

    async def get_server_status(self) -> OllamaServerStatus:
        """Get comprehensive Ollama server status.

        Returns:
            OllamaServerStatus with availability, running models, and metrics.
        """
        try:
            # Check availability and get running models
            available = await self.is_available()
            if not available:
                return OllamaServerStatus(
                    available=False,
                    version=None,
                    running_models=[],
                    installed_models=[],
                    installed_models_count=0,
                    total_vram_gb=0.0,
                )

            # Get running models and installed model count
            running_models = await self.fetch_running_models()
            installed_models = await self.fetch_models()

            # Calculate total VRAM usage
            total_vram_gb = sum(m.size_vram_gb for m in running_models)

            return OllamaServerStatus(
                available=True,
                version=None,  # Could add version endpoint in future
                running_models=running_models,
                installed_models=installed_models,
                installed_models_count=len(installed_models),
                total_vram_gb=total_vram_gb,
            )

        except Exception as e:
            logger.error(f"Failed to get Ollama server status: {e}")
            return OllamaServerStatus(
                available=False,
                version=None,
                running_models=[],
                installed_models=[],
                installed_models_count=0,
                total_vram_gb=0.0,
            )

    def _parse_running_model(self, raw: dict) -> OllamaRunningModel:
        """Parse raw running model entry into OllamaRunningModel.

        Args:
            raw: Raw model data from Ollama /api/ps endpoint.

        Returns:
            Parsed OllamaRunningModel object.
        """
        # Parse expires_at timestamp
        expires_at_str = raw.get("expires_at", "")
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            expires_at = None

        return OllamaRunningModel(
            name=raw.get("name", ""),
            size=raw.get("size", 0),
            size_vram=raw.get("size_vram", 0),
            digest=raw.get("digest", ""),
            expires_at=expires_at,
        )

    def _parse_model(self, raw: dict) -> OllamaModel:
        """Parse raw model entry into OllamaModel.

        Args:
            raw: Raw model data from Ollama API.

        Returns:
            Parsed OllamaModel object.
        """
        name = raw["name"]

        # Parse modified_at timestamp
        modified_at_str = raw.get("modified_at", "")
        try:
            # Ollama uses ISO format with timezone
            modified_at = datetime.fromisoformat(modified_at_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            modified_at = datetime.now()

        # Extract details from nested dict if present
        details = raw.get("details", {})

        return OllamaModel(
            name=name,
            size=raw.get("size", 0),
            digest=raw.get("digest", ""),
            modified_at=modified_at,
            parameter_size=details.get("parameter_size"),
            quantization_level=details.get("quantization_level"),
            family=details.get("family"),
        )
