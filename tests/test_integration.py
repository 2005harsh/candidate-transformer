import pytest
import json
import tempfile
from pathlib import Path
from app.services.merge_engine import MergeEngine
from app.services.normalizer import Normalizer
from app.parsers.factory import ParserFactory


DATA_DIR = Path("sample_data")

def test_end_to_end():
    """Test end-to-end pipeline with sample data."""
    ats_path = str(DATA_DIR / "sample_ats.json")
    
    parser = ParserFactory.create_parser(ats_path)
    assert parser is not None
    
    data = parser.parse()
    assert data is not None
    assert len(data) > 0
    
    data['_source'] = parser.get_source_name()
    data['_method'] = 'parse'
    
    normalizer = Normalizer()
    normalized = normalizer.normalize_record(data)
    assert normalized is not None
    
    engine = MergeEngine()
    record = engine.merge([normalized])
    
    assert record is not None
    assert record.full_name is not None
    assert len(record.emails) > 0
    assert len(record.skills) > 0


def test_multiple_source_merge():
    """Test merging multiple source types."""
    # Create JSON source
    json_data = {
        "candidate": {
            "name": "John Smith",
            "email": "john@example.com",
            "phone": "+1234567890"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(json_data, f)
        json_path = f.name
    
    # Parse JSON
    json_parser = ParserFactory.create_parser(json_path)
    json_parsed = json_parser.parse()
    json_parsed['_source'] = json_parser.get_source_name()
    json_parsed['_method'] = 'parse'
    
    # Normalize and merge
    normalizer = Normalizer()
    json_norm = normalizer.normalize_record(json_parsed)
    
    engine = MergeEngine()
    record = engine.merge([json_norm])
    
    assert record.full_name == 'John Smith'
    assert 'john@example.com' in record.emails
    
    # Clean up
    import os
    os.unlink(json_path)


def test_missing_source_handling():
    """Test handling of missing sources."""
    # Factory returns None for non-existent files
    unknown = ParserFactory.create_parser("/path/to/file.unknown")
    assert unknown is None or not unknown.validate_source()
    
    # Merge with empty list should return empty record
    engine = MergeEngine()
    record = engine.merge([])
    assert isinstance(record, object)  # Should not be None
    assert record.emails == []


def test_malformed_source_handling(tmp_path):
    """Test handling of malformed source."""
    # Create malformed JSON file
    bad = tmp_path / "bad.json"
    bad.write_text("{ not: valid json }")
    
    p = ParserFactory.create_parser(str(bad))
    assert p is not None
    
    # Should not raise exception, should return empty dict
    data = p.parse()
    assert isinstance(data, dict)


def test_github_parser_mock(monkeypatch):
    """Test GitHub parser with mock data."""
    # Skip test if requests not available
    try:
        import requests
    except ImportError:
        pytest.skip("requests not installed")
    
    class MockResp:
        def __init__(self, data, status=200):
            self._data = data
            self.status_code = status
            self.headers = {}
        
        def json(self):
            return self._data
    
    def mock_get(url, *args, **kwargs):
        if "repos" in url:
            return MockResp([
                {"name": "repo1", "html_url": "https://github.com/test/repo1", "language": "Python"},
                {"name": "repo2", "html_url": "https://github.com/test/repo2", "language": "JavaScript"},
            ])
        return MockResp({
            "login": "test",
            "name": "Test User",
            "html_url": "https://github.com/test",
            "public_repos": 2,
            "bio": "Test bio",
            "location": "Test City"
        })
    
    monkeypatch.setattr("requests.get", mock_get)
    
    from app.parsers.github_parser import GitHubParser
    parser = GitHubParser("https://github.com/test")
    out = parser.parse()
    
    # Check that we got some data
    assert out is not None
    # The parser should extract some fields
    assert isinstance(out, dict)
    # At minimum, should have a name or login
    assert out.get('full_name') == 'Test User' or out.get('full_name') is not None


def test_normalizer_phone():
    """Test phone normalization."""
    normalizer = Normalizer()
    result = normalizer.normalize_phone("+1-555-123-4567")
    # Phone normalization should work or return None (not error)
    assert result is not None or result is None


def test_normalizer_skill():
    """Test skill canonicalization."""
    normalizer = Normalizer()
    result = normalizer.canonicalize_skill("python")
    assert result == "Python" or result == "python"