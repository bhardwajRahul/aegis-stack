"""
Tests for BulkInsightsResponse model validation and date coercion.
"""

from datetime import datetime

from app.services.insights.schemas import BulkInsightsResponse


class TestBulkInsightsResponse:
    def test_model_validate_from_json(self) -> None:
        """Constructs from JSON-like dict with string dates."""
        raw = {
            "daily": {
                "clones": [
                    {
                        "date": "2026-04-10T00:00:00",
                        "value": 42.0,
                        "period": "daily",
                        "metric_type_id": 1,
                        "metadata_": {},
                    },
                ]
            },
            "events": {"new_star": []},
            "insight_events": [
                {
                    "date": "2026-04-10T00:00:00",
                    "event_type": "release",
                    "description": "v1.0",
                    "metadata_": {},
                },
            ],
            "sources": [],
            "latest": {"referrers": None},
        }
        bulk = BulkInsightsResponse.model_validate(raw)

        assert len(bulk.daily["clones"]) == 1
        assert len(bulk.insight_events) == 1

    def test_date_coercion_from_string(self) -> None:
        """String dates get coerced to datetime objects via model_post_init."""
        raw = {
            "daily": {
                "clones": [
                    {
                        "date": "2026-04-10T00:00:00",
                        "value": 10.0,
                        "period": "daily",
                        "metric_type_id": 1,
                        "metadata_": {},
                    },
                ]
            },
            "events": {},
            "insight_events": [
                {
                    "date": "2026-04-10T00:00:00",
                    "event_type": "star",
                    "description": "test",
                    "metadata_": {},
                },
            ],
            "sources": [],
            "latest": {},
        }
        bulk = BulkInsightsResponse.model_validate(raw)

        assert isinstance(bulk.daily["clones"][0].date, datetime)
        assert bulk.daily["clones"][0].date == datetime(2026, 4, 10)

        assert isinstance(bulk.insight_events[0].date, datetime)
        assert bulk.insight_events[0].date == datetime(2026, 4, 10)

    def test_datetime_passthrough(self) -> None:
        """Already-datetime dates are not broken by coercion."""
        raw = {
            "daily": {
                "clones": [
                    {
                        "date": datetime(2026, 4, 10),
                        "value": 10.0,
                        "period": "daily",
                        "metric_type_id": 1,
                        "metadata_": {},
                    },
                ]
            },
            "events": {},
            "insight_events": [],
            "sources": [],
            "latest": {},
        }
        bulk = BulkInsightsResponse.model_validate(raw)

        assert isinstance(bulk.daily["clones"][0].date, datetime)
        assert bulk.daily["clones"][0].date == datetime(2026, 4, 10)

    def test_empty_response(self) -> None:
        """Empty data produces valid model."""
        raw = {
            "daily": {},
            "events": {},
            "insight_events": [],
            "sources": [],
            "latest": {},
        }
        bulk = BulkInsightsResponse.model_validate(raw)

        assert bulk.daily == {}
        assert bulk.events == {}
        assert bulk.insight_events == []
        assert bulk.sources == []
        assert bulk.latest == {}

    def test_latest_with_none_values(self) -> None:
        """Latest dict can contain None values."""
        raw = {
            "daily": {},
            "events": {},
            "insight_events": [],
            "sources": [],
            "latest": {"referrers": None, "popular_paths": None},
        }
        bulk = BulkInsightsResponse.model_validate(raw)

        assert bulk.latest["referrers"] is None
        assert bulk.latest["popular_paths"] is None

    def test_attribute_access(self) -> None:
        """Fields accessible via attribute, not dict."""
        raw = {
            "daily": {"clones": []},
            "events": {},
            "insight_events": [],
            "sources": [],
            "latest": {},
        }
        bulk = BulkInsightsResponse.model_validate(raw)

        assert hasattr(bulk, "daily")
        assert bulk.daily["clones"] == []
