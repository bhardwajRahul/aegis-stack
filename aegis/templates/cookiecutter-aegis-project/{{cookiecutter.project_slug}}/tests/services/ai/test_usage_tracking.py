"""Tests for LLM usage tracking service functions."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

from app.services.ai.models.llm import (
    LargeLanguageModel,
    LLMPrice,
    LLMUsage,
    LLMVendor,
)
from app.services.ai.service import AIService
from sqlmodel import Session, select


class TestExtractUsage:
    """Tests for the _extract_usage method."""

    def test_extract_usage_response(self, ai_service: AIService) -> None:
        """Test extracting usage from AI response format.

        The actual format depends on the AI framework used:
        - LangChain: response_metadata.token_usage
        - PydanticAI: result.usage attribute
        """
        mock_result = MagicMock()
        # LangChain format
        mock_result.response_metadata = {
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
            }
        }

        usage = ai_service._extract_usage(mock_result)

        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50

    def test_extract_usage_missing_metadata(self, ai_service: AIService) -> None:
        """Test extracting usage when metadata is missing."""
        mock_result = MagicMock()
        mock_result.usage = None
        mock_result.response_metadata = {}

        usage = ai_service._extract_usage(mock_result)

        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0

    def test_extract_usage_no_usage_attribute(self, ai_service: AIService) -> None:
        """Test extracting usage when result has no usage info."""
        mock_result = MagicMock(spec=[])  # Empty spec, no attributes

        usage = ai_service._extract_usage(mock_result)

        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0


class TestRecordUsage:
    """Tests for the _record_usage method."""

    @contextmanager
    def _mock_db_session(self, session: Session) -> Generator[MagicMock, None, None]:
        """Create a mock db_session context manager that uses our test session."""

        @contextmanager
        def mock_session_cm() -> Generator[Session, None, None]:
            yield session

        with patch("app.services.ai.service.db_session", mock_session_cm):
            yield mock_session_cm

    def test_record_usage_success(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        sample_price: LLMPrice,
        mock_ai_settings: Any,
    ) -> None:
        """Test recording usage creates an LLMUsage record."""
        mock_ai_settings.AI_MODEL = "gpt-4o"
        service = AIService(mock_ai_settings)

        with self._mock_db_session(db_session):
            service._record_usage(
                action="chat",
                usage={"input_tokens": 100, "output_tokens": 50},
                user_id="user-123",
                success=True,
            )

        # Verify usage was recorded
        stmt = select(LLMUsage).where(LLMUsage.user_id == "user-123")
        usage_record = db_session.exec(stmt).first()

        assert usage_record is not None
        assert usage_record.action == "chat"
        assert usage_record.input_tokens == 100
        assert usage_record.output_tokens == 50
        assert usage_record.success is True
        assert usage_record.llm_id == sample_llm.id

    def test_record_usage_calculates_cost_correctly(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        sample_price: LLMPrice,
        mock_ai_settings: Any,
    ) -> None:
        """Test that cost is calculated correctly from token usage and price."""
        mock_ai_settings.AI_MODEL = "gpt-4o"
        service = AIService(mock_ai_settings)

        # Price: input=$5/1M ($0.000005/token), output=$15/1M ($0.000015/token)
        # Usage: 1000 input tokens, 500 output tokens
        # Expected cost: (1000 * 0.000005) + (500 * 0.000015) = 0.005 + 0.0075 = 0.0125
        with self._mock_db_session(db_session):
            service._record_usage(
                action="chat",
                usage={"input_tokens": 1000, "output_tokens": 500},
                user_id="user-456",
            )

        stmt = select(LLMUsage).where(LLMUsage.user_id == "user-456")
        usage_record = db_session.exec(stmt).first()

        assert usage_record is not None
        assert abs(usage_record.total_cost - 0.0125) < 0.0001

    def test_record_usage_missing_llm_logs_warning(
        self,
        db_session: Session,
        mock_ai_settings: Any,
    ) -> None:
        """Test that missing LLM logs a warning but doesn't fail."""
        mock_ai_settings.AI_MODEL = "nonexistent-model"
        service = AIService(mock_ai_settings)

        with self._mock_db_session(db_session):
            # Should not raise, just log warning
            service._record_usage(
                action="chat",
                usage={"input_tokens": 100, "output_tokens": 50},
                user_id="user-789",
            )

        # No usage record should be created
        stmt = select(LLMUsage).where(LLMUsage.user_id == "user-789")
        usage_record = db_session.exec(stmt).first()
        assert usage_record is None

    def test_record_usage_missing_price_zero_cost(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        mock_ai_settings: Any,
    ) -> None:
        """Test that missing price results in zero cost."""
        # Note: sample_price fixture not used - no price in DB
        mock_ai_settings.AI_MODEL = "gpt-4o"
        service = AIService(mock_ai_settings)

        with self._mock_db_session(db_session):
            service._record_usage(
                action="chat",
                usage={"input_tokens": 100, "output_tokens": 50},
                user_id="user-noprice",
            )

        stmt = select(LLMUsage).where(LLMUsage.user_id == "user-noprice")
        usage_record = db_session.exec(stmt).first()

        assert usage_record is not None
        assert usage_record.total_cost == 0.0

    def test_record_usage_with_error(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        sample_price: LLMPrice,
        mock_ai_settings: Any,
    ) -> None:
        """Test recording a failed request with error message."""
        mock_ai_settings.AI_MODEL = "gpt-4o"
        service = AIService(mock_ai_settings)

        with self._mock_db_session(db_session):
            service._record_usage(
                action="chat",
                usage={"input_tokens": 50, "output_tokens": 0},
                user_id="user-error",
                success=False,
                error_message="Rate limit exceeded",
            )

        stmt = select(LLMUsage).where(LLMUsage.user_id == "user-error")
        usage_record = db_session.exec(stmt).first()

        assert usage_record is not None
        assert usage_record.success is False
        assert usage_record.error_message == "Rate limit exceeded"
        assert usage_record.output_tokens == 0

    def test_record_usage_strips_vendor_prefix(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        sample_price: LLMPrice,
        mock_ai_settings: Any,
    ) -> None:
        """Test that vendor prefix is stripped from model name."""
        # Model name with vendor prefix: "openai/gpt-4o"
        mock_ai_settings.AI_MODEL = "openai/gpt-4o"
        service = AIService(mock_ai_settings)

        with self._mock_db_session(db_session):
            service._record_usage(
                action="chat",
                usage={"input_tokens": 100, "output_tokens": 50},
                user_id="user-prefix",
            )

        stmt = select(LLMUsage).where(LLMUsage.user_id == "user-prefix")
        usage_record = db_session.exec(stmt).first()

        # Should find the LLM by stripped model_id "gpt-4o"
        assert usage_record is not None
        assert usage_record.llm_id == sample_llm.id

    def test_record_usage_database_error_doesnt_fail(
        self,
        mock_ai_settings: Any,
    ) -> None:
        """Test that database errors don't crash the request."""
        mock_ai_settings.AI_MODEL = "gpt-4o"
        service = AIService(mock_ai_settings)

        # Mock db_session to raise on context manager entry
        failing_session = MagicMock()
        failing_session.return_value.__enter__.side_effect = Exception(
            "Database connection failed"
        )

        with patch("app.services.ai.service.db_session", failing_session):
            # Should not raise, just log error
            service._record_usage(
                action="chat",
                usage={"input_tokens": 100, "output_tokens": 50},
                user_id="user-fail",
            )

        # Test passes if no exception was raised


class TestGetUsageStats:
    """Tests for get_usage_stats aggregation method."""

    @contextmanager
    def _mock_db_session(self, session: Session) -> Generator[MagicMock, None, None]:
        """Create a mock db_session context manager that uses our test session."""

        @contextmanager
        def mock_session_cm() -> Generator[Session, None, None]:
            yield session

        with patch("app.services.ai.service.db_session", mock_session_cm):
            yield mock_session_cm

    def test_get_usage_stats_empty_database(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        mock_ai_settings: Any,
    ) -> None:
        """Test stats return zeros when no usage records exist."""
        service = AIService(mock_ai_settings)
        with self._mock_db_session(db_session):
            stats = service.get_usage_stats()

        assert stats["total_tokens"] == 0
        assert stats["total_requests"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["success_rate"] == 100.0
        assert stats["models"] == []
        assert stats["recent_activity"] == []

    def test_get_usage_stats_with_data(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        mock_ai_settings: Any,
    ) -> None:
        """Test stats aggregation with usage records."""
        usage1 = LLMUsage(
            llm_id=sample_llm.id,
            user_id="user-1",
            input_tokens=100,
            output_tokens=50,
            total_cost=0.001,
            success=True,
            action="chat",
        )
        usage2 = LLMUsage(
            llm_id=sample_llm.id,
            user_id="user-1",
            input_tokens=200,
            output_tokens=100,
            total_cost=0.002,
            success=True,
            action="chat",
        )
        db_session.add(usage1)
        db_session.add(usage2)
        db_session.commit()

        service = AIService(mock_ai_settings)
        with self._mock_db_session(db_session):
            stats = service.get_usage_stats()

        assert stats["total_tokens"] == 450  # 100+50+200+100
        assert stats["input_tokens"] == 300
        assert stats["output_tokens"] == 150
        assert stats["total_requests"] == 2
        assert abs(stats["total_cost"] - 0.003) < 0.0001
        assert stats["success_rate"] == 100.0

    def test_get_usage_stats_model_breakdown(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        sample_vendor: LLMVendor,
        mock_ai_settings: Any,
    ) -> None:
        """Test model breakdown aggregation."""
        usage = LLMUsage(
            llm_id=sample_llm.id,
            user_id="user-1",
            input_tokens=100,
            output_tokens=50,
            total_cost=0.001,
            success=True,
            action="chat",
        )
        db_session.add(usage)
        db_session.commit()

        service = AIService(mock_ai_settings)
        with self._mock_db_session(db_session):
            stats = service.get_usage_stats()

        assert len(stats["models"]) == 1
        model_stats = stats["models"][0]
        assert model_stats["model_id"] == "gpt-4o"
        assert model_stats["vendor"] == "openai"
        assert model_stats["requests"] == 1
        assert model_stats["percentage"] == 100.0

    def test_get_usage_stats_recent_activity(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        mock_ai_settings: Any,
    ) -> None:
        """Test recent activity returns correct entries."""
        usage = LLMUsage(
            llm_id=sample_llm.id,
            user_id="user-1",
            input_tokens=100,
            output_tokens=50,
            total_cost=0.001,
            success=True,
            action="chat",
        )
        db_session.add(usage)
        db_session.commit()

        service = AIService(mock_ai_settings)
        with self._mock_db_session(db_session):
            stats = service.get_usage_stats(recent_limit=5)

        assert len(stats["recent_activity"]) == 1
        activity = stats["recent_activity"][0]
        assert activity["model"] == "GPT-4o"
        assert activity["tokens"] == 150
        assert activity["success"] is True
        assert activity["action"] == "chat"

    def test_get_usage_stats_user_filter(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        mock_ai_settings: Any,
    ) -> None:
        """Test filtering by user_id."""
        usage1 = LLMUsage(
            llm_id=sample_llm.id,
            user_id="user-1",
            input_tokens=100,
            output_tokens=50,
            total_cost=0.001,
            success=True,
            action="chat",
        )
        usage2 = LLMUsage(
            llm_id=sample_llm.id,
            user_id="user-2",
            input_tokens=200,
            output_tokens=100,
            total_cost=0.002,
            success=True,
            action="chat",
        )
        db_session.add(usage1)
        db_session.add(usage2)
        db_session.commit()

        service = AIService(mock_ai_settings)
        with self._mock_db_session(db_session):
            stats = service.get_usage_stats(user_id="user-1")

        assert stats["total_requests"] == 1
        assert stats["total_tokens"] == 150

    def test_get_usage_stats_success_rate(
        self,
        db_session: Session,
        sample_llm: LargeLanguageModel,
        mock_ai_settings: Any,
    ) -> None:
        """Test success rate calculation with failures."""
        usage1 = LLMUsage(
            llm_id=sample_llm.id,
            user_id="user-1",
            input_tokens=100,
            output_tokens=50,
            total_cost=0.001,
            success=True,
            action="chat",
        )
        usage2 = LLMUsage(
            llm_id=sample_llm.id,
            user_id="user-1",
            input_tokens=100,
            output_tokens=0,
            total_cost=0.0,
            success=False,
            action="chat",
            error_message="Provider error",
        )
        db_session.add(usage1)
        db_session.add(usage2)
        db_session.commit()

        service = AIService(mock_ai_settings)
        with self._mock_db_session(db_session):
            stats = service.get_usage_stats()

        assert stats["total_requests"] == 2
        assert stats["success_rate"] == 50.0
