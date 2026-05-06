"""Tests for read_jsonc.py — JSONC comment stripping and parsing."""
import json
import sys
import textwrap
import tempfile
from pathlib import Path

import pytest

# Allow import from parent directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from read_jsonc import read_jsonc


# ── helpers ────────────────────────────────────────────────────────────────────

def _write_tmp(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonc', delete=False,
                                    encoding='utf-8')
    f.write(textwrap.dedent(content))
    f.close()
    return Path(f.name)


# ── tests ──────────────────────────────────────────────────────────────────────

def test_plain_json():
    p = _write_tmp('{"a": 1, "b": "hello"}')
    result = read_jsonc(p)
    assert result == {"a": 1, "b": "hello"}


def test_single_line_comment_stripped():
    p = _write_tmp("""\
        {
          // this is a comment
          "key": 42
        }
    """)
    result = read_jsonc(p)
    assert result == {"key": 42}


def test_inline_comment_stripped():
    p = _write_tmp("""\
        {
          "key": 99  // inline comment
        }
    """)
    result = read_jsonc(p)
    assert result == {"key": 99}


def test_url_in_string_not_stripped():
    """Double-slash inside a string value must not be treated as a comment."""
    p = _write_tmp("""\
        {
          "url": "https://example.com/path"
        }
    """)
    result = read_jsonc(p)
    assert result["url"] == "https://example.com/path"


def test_nested_object():
    p = _write_tmp("""\
        {
          // top-level comment
          "grid": {
            "size": 15,    // grid size
            "spacing": 2.0
          }
        }
    """)
    result = read_jsonc(p)
    assert result["grid"]["size"] == 15
    assert result["grid"]["spacing"] == 2.0


def test_array_value():
    p = _write_tmp("""\
        {
          "position": [40, 40, 25]  // BS position
        }
    """)
    result = read_jsonc(p)
    assert result["position"] == [40, 40, 25]


def test_scientific_notation():
    p = _write_tmp('{"freq": 3.5e9, "bw": 1e8}')
    result = read_jsonc(p)
    assert result["freq"] == pytest.approx(3.5e9)
    assert result["bw"] == pytest.approx(1e8)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_jsonc(Path("/nonexistent/path/config.jsonc"))


def test_invalid_json_raises():
    p = _write_tmp('{ "key": }')
    with pytest.raises(json.JSONDecodeError):
        read_jsonc(p)


def test_real_config_parses(tmp_path):
    """Smoke-test: the actual ne_bs config must parse without error."""
    config_path = (Path(__file__).resolve()
                   .parent.parent.parent.parent.parent
                   / 'configs' / 'ne_bs_voronoi_15x15_config.jsonc')
    if not config_path.exists():
        pytest.skip(f"Config not found: {config_path}")
    result = read_jsonc(config_path)
    assert result["experiment"]["name"] == "ne_bs_voronoi_15x15"
    assert result["base_station"]["position"] == [48, 48, 10]
    assert result["grid"]["size"] == 15
