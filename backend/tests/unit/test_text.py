from app.ingestion.normalizer.text import make_snippet, strip_html


class TestStripHtml:
    def test_removes_tags(self):
        assert strip_html("<p>Hello <b>World</b></p>") == "Hello World"

    def test_decodes_entities(self):
        assert strip_html("&amp; &lt; &gt; &quot; &#39; &nbsp;") == "& < > \" '"

    def test_empty_string(self):
        assert strip_html("") == ""

    def test_removes_style_block(self):
        assert strip_html("<style>body { color: red; }</style><p>text</p>") == "text"

    def test_removes_script_block(self):
        assert strip_html("<script>alert(1)</script>content") == "content"

    def test_collapses_whitespace(self):
        result = strip_html("<p>  lots   of   space  </p>")
        assert "  " not in result

    def test_plain_text_passthrough(self):
        assert strip_html("just text") == "just text"


class TestMakeSnippet:
    def test_short_text_unchanged(self):
        assert make_snippet("Hello world") == "Hello world"

    def test_truncates_long_text(self):
        text = "word " * 200  # well over 500 chars
        result = make_snippet(text)
        assert result.endswith("...")
        assert len(result) <= 504  # 500 chars + "..."

    def test_truncates_at_word_boundary(self):
        text = "a" * 490 + " boundary_word_here"
        result = make_snippet(text)
        assert not result.endswith("boundary_word_here...")

    def test_strips_html_before_truncating(self):
        assert make_snippet("<p>Hello</p>") == "Hello"

    def test_custom_max_chars(self):
        result = make_snippet("one two three four five", max_chars=10)
        assert len(result) <= 13  # 10 + "..."
