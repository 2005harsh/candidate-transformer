import requests
import re
from typing import Dict, Any
from .base import BaseParser


class GitHubParser(BaseParser):
    """Parser for GitHub profile URLs."""
    
    def __init__(self, source_path: str):
        """Initialize GitHub parser."""
        super().__init__(source_path)
        # Store source_url for use in parse method
        self.source_url = source_path if self._is_url(source_path) else None
        self.username = self._extract_username(source_path)
        print(f"GitHub parser initialized for: {source_path}")
        print(f"Extracted username: {self.username}")
    
    def _extract_username(self, url: str) -> str:
        """Extract GitHub username from URL."""
        if not url:
            return None
        match = re.search(r'github\.com/([a-zA-Z0-9-]+)', url)
        return match.group(1) if match else None
    
    def parse(self) -> Dict[str, Any]:
        """Fetch and parse GitHub profile data."""
        if not self.username:
            print(f"Could not extract username from: {self.source_url}")
            return {}
        
        try:
            # Fetch user data from GitHub API
            print(f"Fetching GitHub data for: {self.username}")
            response = requests.get(
                f'https://api.github.com/users/{self.username}',
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=10
            )
            
            if response.status_code == 404:
                print(f"GitHub user not found: {self.username}")
                return {}
            elif response.status_code != 200:
                print(f"GitHub API error: {response.status_code}")
                return {}
            
            user_data = response.json()
            result = {}
            
            # Extract basic info
            if user_data.get('name'):
                result['full_name'] = user_data['name']
            elif user_data.get('login'):
                result['full_name'] = user_data['login']
            
            if user_data.get('bio'):
                result['headline'] = user_data['bio']
            
            if user_data.get('location'):
                result['location'] = {'city': user_data['location']}
            
            if user_data.get('company'):
                result['current_company'] = user_data['company'].strip('@')
            
            # Links
            links = []
            if user_data.get('html_url'):
                links.append({'type': 'github', 'url': user_data['html_url']})
            if user_data.get('blog'):
                links.append({'type': 'portfolio', 'url': user_data['blog']})
            if links:
                result['links'] = links
            
            # Try to get repositories for languages
            try:
                repos_response = requests.get(
                    f'https://api.github.com/users/{self.username}/repos',
                    headers={'Accept': 'application/vnd.github.v3+json'},
                    params={'per_page': 50, 'sort': 'updated'},
                    timeout=10
                )
                
                if repos_response.status_code == 200:
                    repos = repos_response.json()
                    languages = {}
                    for repo in repos:
                        if repo.get('language') and repo['language']:
                            languages[repo['language']] = languages.get(repo['language'], 0) + 1
                    
                    if languages:
                        skills = []
                        for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]:
                            if lang and lang != 'null':
                                confidence = min(1.0, 0.3 + (count / 50))
                                skills.append({'name': lang, 'confidence': confidence})
                        if skills:
                            result['skills'] = skills
            except Exception as e:
                print(f"Error fetching repos: {e}")
            
            print(f"Extracted {len(result)} fields from GitHub")
            return result
            
        except requests.RequestException as e:
            print(f"GitHub API request error: {e}")
            return {}
        except Exception as e:
            print(f"Error parsing GitHub data: {e}")
            return {}
    
    def get_source_name(self) -> str:
        return f"github_{self.username}" if self.username else "github_unknown"
    
    def validate_source(self) -> bool:
        """Validate that the GitHub username is accessible."""
        if not self.username:
            return False
        
        try:
            response = requests.head(
                f'https://api.github.com/users/{self.username}',
                timeout=5
            )
            return response.status_code == 200
        except:
            return False