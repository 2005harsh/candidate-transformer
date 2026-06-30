import pytest
from app.services.merge_engine import MergeEngine
from app.services.normalizer import Normalizer


class TestMerge:
    
    def setup_method(self):
        self.engine = MergeEngine()
        self.normalizer = Normalizer()
        
        # Sample records
        self.record_ats = {
            "_source": "ats",
            "candidate_id": "c1",
            "name": "Alex Johnson",
            "emails": ["alex.johnson@example.com"],
            "phones": ["+1 555 123 4567"],
            "location": {"city": "San Francisco", "state": "California"},
            "skills": [{"name": "Python", "confidence": 0.9}],
            "experience": [{"company": "Acme Corp", "title": "Senior Engineer", "start": "2019-06", "end": "2024-05"}],
            "education": [{"institution": "State University", "degree": "B.S.", "field": "CS", "end_year": 2015}]
        }
        
        self.record_resume = {
            "_source": "resume",
            "candidate_id": "c2",
            "name": "Alex Johnson",
            "emails": ["alex.j@example.com"],
            "phones": ["(555)123-4567"],
            "skills": [{"name": "Python", "confidence": 0.8}]
        }
    
    def test_basic_merge(self):
        """Test basic merge functionality."""
        sources = [
            {
                '_source': 'ats_test',
                '_method': 'parse',
                'full_name': 'John Doe',
                'emails': ['john@example.com'],
                'phones': ['+1234567890']
            },
            {
                '_source': 'resume_test',
                '_method': 'parse',
                'full_name': 'John Doe',
                'emails': ['john.doe@example.com'],
                'skills': [{'name': 'Python'}, {'name': 'JavaScript'}]
            }
        ]
        
        record = self.engine.merge(sources)
        
        assert record.full_name == 'John Doe'
        assert len(record.emails) == 2
        assert '+1234567890' in record.phones
        assert len(record.skills) >= 1
    
    def test_conflict_resolution(self):
        """Test conflict resolution when fields conflict."""
        # Use dicts with _source for proper merging
        source1 = {
            '_source': 'ats_test',
            '_method': 'parse',
            'full_name': 'John Smith'
        }
        
        source2 = {
            '_source': 'resume_test',
            '_method': 'parse',
            'full_name': 'Jonathan Smith'
        }
        
        record = self.engine.merge([source1, source2])
        # First source should win
        assert record.full_name == 'John Smith'
    
    def test_deduplication(self):
        """Test deduplication of list fields."""
        sources = [
            {
                '_source': 'source1',
                '_method': 'parse',
                'emails': ['john@example.com', 'john.doe@example.com'],
                'phones': ['+1234567890']
            },
            {
                '_source': 'source2',
                '_method': 'parse',
                'emails': ['john@example.com'],  # Duplicate
                'phones': ['+9876543210']
            }
        ]
        
        record = self.engine.merge(sources)
        
        assert len(record.emails) == 2
        assert 'john@example.com' in record.emails
        assert 'john.doe@example.com' in record.emails
        assert len(record.phones) == 2
    
    def test_identity_matching(self):
        """Test identity matching across sources."""
        # This should test the _are_same_candidate method
        # But we'll test the merge result instead
        source1 = {
            '_source': 'source1',
            '_method': 'parse',
            'full_name': 'Jane Smith',
            'emails': ['jane@example.com']
        }
        source2 = {
            '_source': 'source2',
            '_method': 'parse',
            'full_name': 'Jane S.',
            'emails': ['jane@example.com']  # Same email
        }
        
        record = self.engine.merge([source1, source2])
        assert record.full_name == 'Jane Smith'
        assert len(record.emails) == 1
    
    def test_skill_merge(self):
        """Test skill merging with confidence."""
        sources = [
            {
                '_source': 'source1',
                '_method': 'parse',
                'skills': [{'name': 'Python', 'confidence': 0.8}]
            },
            {
                '_source': 'source2',
                '_method': 'parse',
                'skills': [{'name': 'python', 'confidence': 0.9}]  # Same skill, different case
            }
        ]
        
        record = self.engine.merge(sources)
        assert len(record.skills) == 1
        assert record.skills[0].name == 'Python'
        assert record.skills[0].confidence >= 0.8
    
    def test_experience_merge(self):
        """Test experience merging."""
        sources = [
            {
                '_source': 'source1',
                '_method': 'parse',
                'experience': [
                    {'company': 'TechCorp', 'title': 'Engineer', 'start': '2020-01', 'end': '2022-12'}
                ]
            },
            {
                '_source': 'source2',
                '_method': 'parse',
                'experience': [
                    {'company': 'TechCorp', 'title': 'Senior Engineer', 'start': '2020-01', 'end': '2023-12'}
                ]
            }
        ]
        
        record = self.engine.merge(sources)
        assert len(record.experience) == 1
        assert record.experience[0].company == 'TechCorp'
    
    def test_provenance_tracking(self):
        """Test provenance tracking."""
        sources = [
            {
                '_source': 'ats_test',
                '_method': 'parse',
                'full_name': 'John Doe',
                'emails': ['john@example.com']
            }
        ]
        
        record = self.engine.merge(sources)
        assert len(record.provenance) >= 2
        provenance_fields = set(p.field for p in record.provenance)
        assert 'full_name' in provenance_fields
        assert 'emails' in provenance_fields