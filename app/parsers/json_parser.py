import json
from typing import Dict, Any, List
from pathlib import Path
from .base import BaseParser


class JSONParser(BaseParser):
    """Parser for ATS JSON files."""
    
    def parse(self) -> Dict[str, Any]:
        """Parse ATS JSON into raw data."""
        if not self.validate_source():
            print(f"Source validation failed: {self.source_path_str}")
            return {}
        
        try:
            print(f"Reading JSON from: {self.source_path_str}")
            
            # Read with utf-8-sig to handle BOM
            with open(self.source_path_str, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            
            print(f"JSON loaded successfully. Type: {type(data)}")
            
            # Handle different JSON structures
            if isinstance(data, list):
                print("Data is a list, taking first item")
                if data:
                    return self._extract_candidate(data[0])
                return {}
            elif isinstance(data, dict):
                print("Data is a dictionary")
                # Check for nested structures
                if 'candidate' in data:
                    print("Found 'candidate' key")
                    return self._extract_candidate(data['candidate'])
                elif 'profile' in data:
                    print("Found 'profile' key")
                    return self._extract_candidate(data['profile'])
                elif 'data' in data and isinstance(data['data'], dict):
                    print("Found 'data' key")
                    return self._extract_candidate(data['data'])
                else:
                    print("Using top-level data")
                    return self._extract_candidate(data)
            else:
                print(f"Unexpected data type: {type(data)}")
                return {}
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return {}
        except FileNotFoundError as e:
            print(f"File not found: {e}")
            return {}
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return {}
    
    def _extract_candidate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract candidate fields from ATS format."""
        print("Extracting candidate fields...")
        result = {}
        
        # Name - try multiple field names
        for name_field in ['name', 'full_name', 'candidate_name', 'candidateName']:
            if name_field in data and data[name_field]:
                result['full_name'] = str(data[name_field])
                print(f"Found name: {result['full_name']}")
                break
        
        # Email - try multiple field names
        for email_field in ['email', 'emails', 'email_address', 'emailAddress']:
            if email_field in data and data[email_field]:
                if isinstance(data[email_field], list):
                    result['emails'] = [str(e) for e in data[email_field] if e]
                else:
                    result['emails'] = [str(data[email_field])]
                print(f"Found emails: {result['emails']}")
                break
        
        # Phone - try multiple field names
        for phone_field in ['phone', 'phones', 'phone_number', 'phoneNumber']:
            if phone_field in data and data[phone_field]:
                if isinstance(data[phone_field], list):
                    result['phones'] = [str(p) for p in data[phone_field] if p]
                else:
                    result['phones'] = [str(data[phone_field])]
                print(f"Found phones: {result['phones']}")
                break
        
        # Title/Headline
        for title_field in ['title', 'headline', 'job_title', 'jobTitle']:
            if title_field in data and data[title_field]:
                result['headline'] = str(data[title_field])
                print(f"Found headline: {result['headline']}")
                break
        
        # Company
        if 'company' in data and data['company']:
            result['current_company'] = str(data['company'])
            print(f"Found company: {result['current_company']}")
        
        # Location
        if 'location' in data and data['location']:
            if isinstance(data['location'], dict):
                result['location'] = data['location']
                print(f"Found location: {result['location']}")
        
        # Skills
        if 'skills' in data and data['skills']:
            if isinstance(data['skills'], list):
                result['skills'] = []
                for skill in data['skills']:
                    if isinstance(skill, str):
                        result['skills'].append({'name': skill})
                    elif isinstance(skill, dict) and 'name' in skill:
                        result['skills'].append(skill)
                print(f"Found {len(result['skills'])} skills")
        
        # Experience
        if 'experience' in data and data['experience']:
            if isinstance(data['experience'], list):
                result['experience'] = data['experience']
                print(f"Found {len(result['experience'])} experience entries")
        
        # Education
        if 'education' in data and data['education']:
            if isinstance(data['education'], list):
                result['education'] = data['education']
                print(f"Found {len(result['education'])} education entries")
        
        # Links
        if 'links' in data and data['links']:
            if isinstance(data['links'], list):
                result['links'] = data['links']
                print(f"Found {len(result['links'])} links")
        
        # Check for LinkedIn and GitHub separately
        if 'linkedin' in data and data['linkedin']:
            if 'links' not in result:
                result['links'] = []
            result['links'].append({'type': 'linkedin', 'url': str(data['linkedin'])})
            print(f"Found LinkedIn: {data['linkedin']}")
        
        if 'github' in data and data['github']:
            if 'links' not in result:
                result['links'] = []
            result['links'].append({'type': 'github', 'url': str(data['github'])})
            print(f"Found GitHub: {data['github']}")
        
        # Store raw data for reference
        result['_raw'] = data
        print(f"Extraction complete. Found {len(result)} fields")
        
        return result
    
    def get_source_name(self) -> str:
        return f"ats_json_{Path(self.source_path_str).name}"