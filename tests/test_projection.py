import pytest
from app.services.projection import ProjectionEngine
from app.schemas.canonical import CanonicalRecord, Skill, Experience, Location, Link
from app.parsers.csv_parser import CSVParser


def test_default_projection():
    """Test default projection without config."""
    record = CanonicalRecord(
        candidate_id='cand_001',
        full_name='John Doe',
        emails=['john@example.com'],
        phones=['+1234567890'],
        skills=[Skill(name='Python', confidence=0.8), Skill(name='JavaScript', confidence=0.7)]
    )
    
    # Pass empty config for default projection
    engine = ProjectionEngine({})
    result = engine.project(record)
    
    assert result['full_name'] == 'John Doe'
    assert 'john@example.com' in result['emails']
    assert len(result['skills']) == 2


def test_custom_field_projection():
    """Test projection with custom field config."""
    record = CanonicalRecord(
        full_name='John Doe',
        emails=['john@example.com', 'john.doe@example.com'],
        phones=['+1234567890'],
        skills=[Skill(name='Python'), Skill(name='JavaScript')]
    )
    
    config = {
        'fields': [
            {'path': 'name', 'from': 'full_name', 'type': 'string', 'required': True},
            {'path': 'primary_email', 'from': 'emails[0]', 'type': 'string', 'required': True},
            {'path': 'phone', 'from': 'phones[0]', 'type': 'string'},
            {'path': 'skills', 'from': 'skills', 'type': 'string[]'}
        ]
    }
    
    engine = ProjectionEngine(config)
    result = engine.project(record)
    
    assert result['name'] == 'John Doe'
    assert result['primary_email'] == 'john@example.com'
    assert result['phone'] == '+1234567890'
    assert len(result['skills']) == 2


def test_missing_field_handling():
    """Test handling of missing fields."""
    record = CanonicalRecord(full_name='John Doe')
    
    config = {
        'fields': [
            {'path': 'name', 'from': 'full_name', 'type': 'string', 'required': True},
            {'path': 'email', 'from': 'emails[0]', 'type': 'string', 'on_missing': 'null'}
        ]
    }
    
    engine = ProjectionEngine(config)
    result = engine.project(record)
    
    assert result['name'] == 'John Doe'
    assert result['email'] is None


def test_mapping_config_projection():
    """Test projection with mapping-style configuration."""
    record = CanonicalRecord(
        full_name='Jane Doe',
        emails=['jane@example.com']
    )

    config = {
        'mapping': {
            'candidate_name': 'full_name',
            'candidate_email': 'emails[0]'
        },
        'options': {
            'include_provenance': False,
            'include_confidence': True,
            'missing': 'null'
        }
    }

    engine = ProjectionEngine(config)
    result = engine.project(record)

    assert result['candidate_name'] == 'Jane Doe'
    assert result['candidate_email'] == 'jane@example.com'
    assert '_confidence' in result
    assert '_provenance' not in result


def test_field_renaming():
    """Test field renaming."""
    record = CanonicalRecord(
        full_name='John Doe',
        emails=['john@example.com']
    )
    
    config = {
        'fields': [
            {'path': 'candidate_name', 'from': 'full_name', 'type': 'string'},
            {'path': 'candidate_email', 'from': 'emails[0]', 'type': 'string'}
        ]
    }
    
    engine = ProjectionEngine(config)
    result = engine.project(record)
    
    assert result['candidate_name'] == 'John Doe'
    assert result['candidate_email'] == 'john@example.com'


def test_csv_parser_parses_all_rows():
    """Test that the CSV parser returns all candidate rows with canonical field names."""
    parser = CSVParser('sample_data/recruiter_export.csv')
    candidates = parser.parse()

    assert len(candidates) == 3
    first = candidates[0]
    assert first['full_name'] == 'Alex Johnson'
    assert first['emails'] == ['alex.johnson@example.com']
    assert first['phones'] == ['+1 555 123 4567']
    assert first['headline'] == 'Senior Software Engineer'
    assert first['current_company'] == 'Acme Corp'
    assert first['location']['city'] == 'San Francisco'
    assert first['location']['region'] == 'CA'
    assert first['skills'][0]['name'] == 'Python'


def test_skill_normalization():
    """Test skill normalization in projection."""
    record = CanonicalRecord(
        skills=[
            Skill(name='python', confidence=0.9),
            Skill(name='reactjs', confidence=0.8),
            Skill(name='node.js', confidence=0.7)
        ]
    )
    
    # Create a projection that doesn't normalize by default
    # The normalization is handled by the normalizer, not projection
    config = {
        'fields': [
            {'path': 'skills', 'from': 'skills', 'type': 'object'}
        ]
    }
    
    engine = ProjectionEngine(config)
    result = engine.project(record)
    
    # Skills should be preserved as objects
    assert len(result['skills']) == 3


def test_type_transformation():
    """Test type transformation in projection."""
    record = CanonicalRecord(
        years_experience=5.0,
        full_name='John Doe'
    )
    
    config = {
        'fields': [
            {'path': 'years', 'from': 'years_experience', 'type': 'string'},
            {'path': 'is_experienced', 'from': 'years_experience', 'type': 'boolean'}
        ]
    }
    
    engine = ProjectionEngine(config)
    result = engine.project(record)
    
    # String conversion
    assert result['years'] == '5.0' or result['years'] == '5'
    # Boolean conversion (should be True for 5.0)
    assert result['is_experienced'] is True