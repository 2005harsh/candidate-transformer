import re
from typing import Dict, Any
from .base import BaseParser


class TXTParser(BaseParser):
    """Parser for text files (Recruiter Notes)."""
    
    def __init__(self, source_path: str):
        """Initialize the TXT parser."""
        super().__init__(source_path)
        # Remove the problematic source_type assignment
    
    def parse(self) -> Dict[str, Any]:
        """Parse text file into candidate data."""
        if not self.validate_source():
            return {}
        
        try:
            with open(self.source_path_str, 'r', encoding='utf-8') as f:
                text = f.read()
            return self._extract_fields(text)
        except Exception as e:
            print(f"Error parsing text from {self.source_path_str}: {e}")
            return {}
    
    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """Extract candidate fields from free text."""
        result = {'_raw_text': text[:500]}  # Store preview
        
        # Try to extract name
        name_patterns = [
            r'(?:Name|Candidate|Full Name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:is|has|works|joined)',
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE)
            if name_match:
                result['full_name'] = name_match.group(1)
                break
        
        # If no name found, try first line
        if not result.get('full_name'):
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if lines and len(lines[0]) < 50:
                result['full_name'] = lines[0]
        
        # Try to extract email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        if emails:
            result['emails'] = list(set(emails))
        
        # Try to extract phone
        phone_patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        ]
        
        phones = []
        for pattern in phone_patterns:
            found = re.findall(pattern, text)
            if found:
                phones.extend(found)
        
        if phones:
            result['phones'] = list(set(phones))
        
        # Try to extract LinkedIn
        linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9-]+'
        linkedin = re.findall(linkedin_pattern, text, re.IGNORECASE)
        
        # Try to extract GitHub
        github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9-]+'
        github = re.findall(github_pattern, text, re.IGNORECASE)
        
        links = []
        if linkedin:
            links.append({'type': 'linkedin', 'url': linkedin[0]})
        if github:
            links.append({'type': 'github', 'url': github[0]})
        
        if links:
            result['links'] = links
        
        # Try to extract skills
        skill_patterns = [
            r'(?:Skills|Skills:|Technical Skills|Technologies|Expertise)[:\s]+([^\n]+)',
            r'proficient in ([^\n]+)',
            r'expertise in ([^\n]+)',
            r'experienced with ([^\n]+)',
        ]
        
        skills = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Split by common delimiters
                skill_list = re.split(r'[,;•\n|]', match)
                for skill in skill_list:
                    skill = skill.strip()
                    if skill and len(skill) > 1 and len(skill) < 50:
                        skills.append({'name': skill})
        
        if skills:
            result['skills'] = skills[:20]
        
        # Try to extract location
        location_patterns = [
            r'(?:Location|Based in|Located in)[:\s]+([^\n]+)',
            r'([A-Z][a-z]+,\s+[A-Z]{2})',
        ]
        
        for pattern in location_patterns:
            loc_match = re.search(pattern, text, re.IGNORECASE)
            if loc_match:
                loc_parts = loc_match.group(1).split(',')
                if len(loc_parts) >= 2:
                    result['location'] = {
                        'city': loc_parts[0].strip(),
                        'region': loc_parts[1].strip(),
                    }
                else:
                    result['location'] = {'city': loc_parts[0].strip()}
                break
        
        # Try to extract experience years
        exp_pattern = r'(\d+)\+?\s+years?\s+of\s+experience'
        exp_match = re.search(exp_pattern, text, re.IGNORECASE)
        if exp_match:
            try:
                result['years_experience'] = float(exp_match.group(1))
            except:
                pass
        
        return result
    
    def get_source_name(self) -> str:
        return f"recruiter_notes_{self.source_path_str.split('/')[-1].split('\\')[-1]}"