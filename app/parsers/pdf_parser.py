import pdfplumber
import re
from typing import Dict, Any
from .base import BaseParser


class PDFParser(BaseParser):
    """Parser for PDF resume files."""
    
    def parse(self) -> Dict[str, Any]:
        """Parse PDF into raw data."""
        if not self.validate_source():
            return {}
        
        try:
            print(f"Reading PDF from: {self.source_path}")
            text = ""
            with pdfplumber.open(self.source_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            print(f"Extracted {len(text)} characters from PDF")
            return self._extract_fields(text)
            
        except Exception as e:
            print(f"Error parsing PDF from {self.source_path}: {e}")
            return {}
    
    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """Extract candidate fields from raw text."""
        result = {}
        
        lines = text.split('\n')
        lines = [l.strip() for l in lines if l.strip()]
        
        if not lines:
            return result
        
        # Try to find name (usually first line)
        if lines:
            if lines[0].lower() in ['resume', 'cv', 'curriculum vitae']:
                if len(lines) > 1:
                    result['full_name'] = lines[1]
            else:
                result['full_name'] = lines[0]
        
        # Find email using regex
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        if emails:
            result['emails'] = list(set(emails))
        
        # Find phone using regex
        phone_pattern = r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            result['phones'] = list(set(phones))
        
        # Try to find LinkedIn/GitHub links
        linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9-]+'
        github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9-]+'
        
        links = []
        linkedin = re.findall(linkedin_pattern, text, re.IGNORECASE)
        if linkedin:
            links.append({'type': 'linkedin', 'url': linkedin[0]})
        
        github = re.findall(github_pattern, text, re.IGNORECASE)
        if github:
            links.append({'type': 'github', 'url': github[0]})
        
        if links:
            result['links'] = links
        
        # Try to extract skills
        skill_sections = re.findall(
            r'(?:Skills|Technical Skills|Expertise|Technologies)[:\s]+([^\n]+)',
            text,
            re.IGNORECASE
        )
        
        if skill_sections:
            skills = []
            for section in skill_sections:
                skill_list = re.split(r'[,;•\n|]', section)
                for skill in skill_list:
                    skill = skill.strip()
                    if skill and len(skill) > 1 and len(skill) < 50:
                        skills.append({'name': skill})
            
            if skills:
                result['skills'] = skills[:20]
        
        return result
    
    def get_source_name(self) -> str:
        return f"resume_pdf_{self.source_path.name}"