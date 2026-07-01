import base64
import json
from datetime import UTC, datetime

from app.routers.jobs import _decode_cursor, _encode_cursor


class TestCursorPagination:
    def test_roundtrip_with_timestamp(self):
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        cursor = _encode_cursor(dt, "abc-123")
        result = _decode_cursor(cursor)
        assert result is not None
        posted_at, job_id = result
        assert posted_at == dt
        assert job_id == "abc-123"

    def test_roundtrip_with_null_posted_at(self):
        cursor = _encode_cursor(None, "xyz-789")
        result = _decode_cursor(cursor)
        assert result is not None
        posted_at, job_id = result
        assert posted_at is None
        assert job_id == "xyz-789"

    def test_invalid_base64_returns_none(self):
        assert _decode_cursor("not-valid-base64!!!") is None

    def test_garbage_json_returns_none(self):
        junk = base64.urlsafe_b64encode(b"not valid json").decode()
        assert _decode_cursor(junk) is None

    def test_missing_keys_returns_none(self):
        bad = base64.urlsafe_b64encode(json.dumps({"x": "y"}).encode()).decode()
        assert _decode_cursor(bad) is None
