import base64
import json

from app.routers.jobs import _decode_cursor


class TestCursorPagination:
    def test_invalid_base64_returns_none(self):
        assert _decode_cursor("not-valid-base64!!!") is None

    def test_garbage_json_returns_none(self):
        junk = base64.urlsafe_b64encode(b"not valid json").decode()
        assert _decode_cursor(junk) is None

    def test_missing_keys_returns_none(self):
        bad = base64.urlsafe_b64encode(json.dumps({"x": "y"}).encode()).decode()
        assert _decode_cursor(bad) is None
