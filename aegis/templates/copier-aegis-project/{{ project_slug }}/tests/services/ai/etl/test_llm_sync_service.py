"""Tests for LLM sync service including Ollama integration."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.ai.etl.clients.ollama_client import OllamaModel
from app.services.ai.etl.llm_sync_service import (
    VENDOR_METADATA,
    LLMSyncService,
    SyncResult,
)
from app.services.ai.models.llm import (
    LargeLanguageModel,
    LLMVendor,
)
from sqlmodel import Session, select

# =============================================================================
# TestSyncOllama
# =============================================================================


class TestSyncOllama:
    """Tests for Ollama model synchronization."""

    @pytest.mark.asyncio
    async def test_sync_ollama_success(
        self,
        etl_session: Session,
        sample_ollama_models: list[OllamaModel],
        mock_ollama_settings: MagicMock,
    ) -> None:
        """Test successful Ollama sync creates models in database."""
        with (
            patch(
                "app.services.ai.etl.llm_sync_service.OllamaClient"
            ) as mock_ollama_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.settings", mock_ollama_settings
            ),
        ):
            mock_client = MagicMock()
            mock_client.is_available = AsyncMock(return_value=True)
            mock_client.fetch_models = AsyncMock(return_value=sample_ollama_models)
            mock_ollama_client_cls.return_value = mock_client

            service = LLMSyncService(etl_session)
            result = await service.sync_ollama(dry_run=False)

        # Verify SyncResult counts
        assert result.models_added == 2
        assert result.vendors_added == 1  # Ollama vendor created
        assert len(result.errors) == 0

        # Verify models were created in database
        models = etl_session.exec(select(LargeLanguageModel)).all()
        assert len(models) == 2
        model_ids = {m.model_id for m in models}
        assert "llama3.2:latest" in model_ids
        assert "mistral:7b" in model_ids

    @pytest.mark.asyncio
    async def test_sync_ollama_dry_run(
        self,
        etl_session: Session,
        sample_ollama_models: list[OllamaModel],
        mock_ollama_settings: MagicMock,
    ) -> None:
        """Test dry_run=True doesn't modify database."""
        with (
            patch(
                "app.services.ai.etl.llm_sync_service.OllamaClient"
            ) as mock_ollama_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.settings", mock_ollama_settings
            ),
        ):
            mock_client = MagicMock()
            mock_client.is_available = AsyncMock(return_value=True)
            mock_client.fetch_models = AsyncMock(return_value=sample_ollama_models)
            mock_ollama_client_cls.return_value = mock_client

            service = LLMSyncService(etl_session)
            result = await service.sync_ollama(dry_run=True)

        # Verify SyncResult reports what would happen
        assert result.models_added == 2
        assert result.vendors_added == 1

        # Verify no actual database changes
        models = etl_session.exec(select(LargeLanguageModel)).all()
        assert len(models) == 0
        vendors = etl_session.exec(select(LLMVendor)).all()
        assert len(vendors) == 0

    @pytest.mark.asyncio
    async def test_sync_ollama_server_unavailable(
        self,
        etl_session: Session,
        mock_ollama_settings: MagicMock,
    ) -> None:
        """Test graceful handling when Ollama server is unavailable."""
        with (
            patch(
                "app.services.ai.etl.llm_sync_service.OllamaClient"
            ) as mock_ollama_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.settings", mock_ollama_settings
            ),
        ):
            mock_client = MagicMock()
            mock_client.is_available = AsyncMock(return_value=False)
            mock_ollama_client_cls.return_value = mock_client

            service = LLMSyncService(etl_session)
            result = await service.sync_ollama(dry_run=False)

        # Verify graceful handling with error message
        assert result.models_added == 0
        assert result.vendors_added == 0
        assert len(result.errors) == 1
        assert "Cannot connect to Ollama" in result.errors[0]

    @pytest.mark.asyncio
    async def test_sync_ollama_creates_vendor(
        self,
        etl_session: Session,
        sample_ollama_models: list[OllamaModel],
        mock_ollama_settings: MagicMock,
    ) -> None:
        """Test Ollama vendor is created with correct metadata."""
        with (
            patch(
                "app.services.ai.etl.llm_sync_service.OllamaClient"
            ) as mock_ollama_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.settings", mock_ollama_settings
            ),
        ):
            mock_client = MagicMock()
            mock_client.is_available = AsyncMock(return_value=True)
            mock_client.fetch_models = AsyncMock(return_value=sample_ollama_models)
            mock_ollama_client_cls.return_value = mock_client

            service = LLMSyncService(etl_session)
            await service.sync_ollama(dry_run=False)

        # Verify Ollama vendor was created with correct metadata
        vendor = etl_session.exec(
            select(LLMVendor).where(LLMVendor.name == "ollama")
        ).first()
        assert vendor is not None
        assert vendor.name == "ollama"
        assert vendor.description == VENDOR_METADATA["ollama"]["description"]
        assert vendor.color == VENDOR_METADATA["ollama"]["color"]
        assert vendor.api_base == VENDOR_METADATA["ollama"]["api_base"]

    @pytest.mark.asyncio
    async def test_sync_ollama_updates_existing_model(
        self,
        etl_session: Session,
        ollama_vendor: LLMVendor,
        existing_ollama_model: LargeLanguageModel,
        mock_ollama_settings: MagicMock,
    ) -> None:
        """Test that syncing updates existing models, not duplicates them."""
        # Sync with updated model data (different quantization)
        updated_ollama_models = [
            OllamaModel(
                name="llama3.2:latest",
                size=2500000000,
                digest="updated_digest",
                modified_at=datetime(2024, 11, 1, 0, 0, 0, tzinfo=UTC),
                parameter_size="3B",
                quantization_level="Q4_K_M",  # Different quantization
                family="llama",
            ),
        ]

        with (
            patch(
                "app.services.ai.etl.llm_sync_service.OllamaClient"
            ) as mock_ollama_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.settings", mock_ollama_settings
            ),
        ):
            mock_client = MagicMock()
            mock_client.is_available = AsyncMock(return_value=True)
            mock_client.fetch_models = AsyncMock(return_value=updated_ollama_models)
            mock_ollama_client_cls.return_value = mock_client

            service = LLMSyncService(etl_session)
            result = await service.sync_ollama(dry_run=False)

        # Verify model was updated, not duplicated
        assert result.models_added == 0
        assert result.models_updated == 1
        assert result.vendors_added == 0  # Vendor already exists

        models = etl_session.exec(select(LargeLanguageModel)).all()
        assert len(models) == 1
        assert models[0].model_id == "llama3.2:latest"
        # Description should be updated with new metadata
        assert "Q4_K_M" in models[0].description

    @pytest.mark.asyncio
    async def test_sync_ollama_empty_models(
        self,
        etl_session: Session,
        mock_ollama_settings: MagicMock,
    ) -> None:
        """Test sync when Ollama has no models installed."""
        with (
            patch(
                "app.services.ai.etl.llm_sync_service.OllamaClient"
            ) as mock_ollama_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.settings", mock_ollama_settings
            ),
        ):
            mock_client = MagicMock()
            mock_client.is_available = AsyncMock(return_value=True)
            mock_client.fetch_models = AsyncMock(return_value=[])
            mock_ollama_client_cls.return_value = mock_client

            service = LLMSyncService(etl_session)
            result = await service.sync_ollama(dry_run=False)

        assert result.models_added == 0
        assert result.vendors_added == 0
        assert len(result.errors) == 0


# =============================================================================
# TestSyncWithSource
# =============================================================================


class TestSyncWithSource:
    """Tests for sync() source parameter routing."""

    @pytest.mark.asyncio
    async def test_sync_source_ollama(
        self,
        etl_session: Session,
        sample_ollama_models: list[OllamaModel],
        mock_ollama_settings: MagicMock,
    ) -> None:
        """Test that source='ollama' only calls sync_ollama."""
        with (
            patch(
                "app.services.ai.etl.llm_sync_service.OllamaClient"
            ) as mock_ollama_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.settings", mock_ollama_settings
            ),
        ):
            mock_client = MagicMock()
            mock_client.is_available = AsyncMock(return_value=True)
            mock_client.fetch_models = AsyncMock(return_value=sample_ollama_models)
            mock_ollama_client_cls.return_value = mock_client

            service = LLMSyncService(etl_session)
            result = await service.sync(source="ollama", dry_run=False)

        # Should have synced Ollama models
        assert result.models_added == 2
        assert result.vendors_added == 1

    @pytest.mark.asyncio
    async def test_sync_source_cloud(
        self,
        etl_session: Session,
    ) -> None:
        """Test that source='cloud' only calls cloud sync."""
        with (
            patch(
                "app.services.ai.etl.llm_sync_service.LiteLLMClient"
            ) as mock_litellm_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.OpenRouterClient"
            ) as mock_openrouter_client_cls,
        ):
            # Mock empty cloud responses
            mock_litellm_client_cls.return_value.fetch_models = AsyncMock(
                return_value=[]
            )
            mock_openrouter_client_cls.return_value.fetch_models = AsyncMock(
                return_value=[]
            )

            service = LLMSyncService(etl_session)
            result = await service.sync(source="cloud", dry_run=False)

        # Should have attempted cloud sync (no models found is fine)
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_sync_source_all(
        self,
        etl_session: Session,
        sample_ollama_models: list[OllamaModel],
        mock_ollama_settings: MagicMock,
    ) -> None:
        """Test that source='all' calls both cloud and ollama sync."""
        with (
            patch(
                "app.services.ai.etl.llm_sync_service.OllamaClient"
            ) as mock_ollama_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.LiteLLMClient"
            ) as mock_litellm_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.OpenRouterClient"
            ) as mock_openrouter_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.settings", mock_ollama_settings
            ),
        ):
            # Mock Ollama client
            mock_ollama = MagicMock()
            mock_ollama.is_available = AsyncMock(return_value=True)
            mock_ollama.fetch_models = AsyncMock(return_value=sample_ollama_models)
            mock_ollama_client_cls.return_value = mock_ollama

            # Mock cloud clients with empty responses
            mock_litellm_client_cls.return_value.fetch_models = AsyncMock(
                return_value=[]
            )
            mock_openrouter_client_cls.return_value.fetch_models = AsyncMock(
                return_value=[]
            )

            service = LLMSyncService(etl_session)
            result = await service.sync(source="all", dry_run=False)

        # Should have synced Ollama models (cloud had none)
        assert result.models_added == 2
        assert result.vendors_added == 1  # Ollama vendor

    @pytest.mark.asyncio
    async def test_sync_source_all_combines_errors(
        self,
        etl_session: Session,
        mock_ollama_settings: MagicMock,
    ) -> None:
        """Test that source='all' combines errors from both sources."""
        with (
            patch(
                "app.services.ai.etl.llm_sync_service.OllamaClient"
            ) as mock_ollama_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.LiteLLMClient"
            ) as mock_litellm_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.OpenRouterClient"
            ) as mock_openrouter_client_cls,
            patch(
                "app.services.ai.etl.llm_sync_service.settings", mock_ollama_settings
            ),
        ):
            # Mock Ollama client - available but will raise error on fetch
            mock_ollama = MagicMock()
            mock_ollama.is_available = AsyncMock(return_value=True)
            mock_ollama.fetch_models = AsyncMock(
                side_effect=Exception("Ollama fetch error")
            )
            mock_ollama_client_cls.return_value = mock_ollama

            # Mock cloud clients
            mock_litellm_client_cls.return_value.fetch_models = AsyncMock(
                return_value=[]
            )
            mock_openrouter_client_cls.return_value.fetch_models = AsyncMock(
                return_value=[]
            )

            service = LLMSyncService(etl_session)
            result = await service.sync(source="all", dry_run=False)

        # Should have error from Ollama fetch
        assert len(result.errors) >= 1
        assert any("Ollama" in e for e in result.errors)


# =============================================================================
# TestSyncResult
# =============================================================================


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_total_synced(self) -> None:
        """Test total_synced property calculation."""
        result = SyncResult(
            vendors_added=2,
            vendors_updated=1,
            models_added=10,
            models_updated=5,
        )
        assert result.total_synced == 18  # 2 + 1 + 10 + 5

    def test_total_synced_empty(self) -> None:
        """Test total_synced with empty result."""
        result = SyncResult()
        assert result.total_synced == 0

    def test_errors_list(self) -> None:
        """Test errors list initialization."""
        result = SyncResult()
        assert result.errors == []

        result.errors.append("Test error")
        assert len(result.errors) == 1


# =============================================================================
# TestVendorMetadata
# =============================================================================


class TestVendorMetadata:
    """Tests for vendor metadata configuration."""

    def test_ollama_metadata_exists(self) -> None:
        """Test that Ollama has vendor metadata defined."""
        assert "ollama" in VENDOR_METADATA

    def test_ollama_metadata_complete(self) -> None:
        """Test that Ollama metadata has all required fields."""
        ollama_meta = VENDOR_METADATA["ollama"]
        assert "description" in ollama_meta
        assert "color" in ollama_meta
        assert "api_base" in ollama_meta
        assert ollama_meta["api_base"] == "http://localhost:11434/v1"
