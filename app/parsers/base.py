from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
import hashlib


class BaseParser(ABC):
    """Abstract base class for all parsers."""
    
    def __init__(self, source_path: str):
        """Initialize the parser with a source path."""
        self.source_path_str = source_path
        self.source_path = Path(source_path) if not self._is_url(source_path) else None
        self.source_url = source_path if self._is_url(source_path) else None
        # Add source_type attribute to avoid errors
        self.source_type = self._detect_source_type()
        print(f"Parser initialized for: {source_path}")
    
    def _is_url(self, path: str) -> bool:
        """Check if the source is a URL."""
        return path.startswith(('http://', 'https://'))
    
    def _detect_source_type(self) -> str:
        """Detect source type from file extension."""
        if self._is_url(self.source_path_str):
            if 'github.com' in self.source_path_str:
                return 'github'
            return 'url'
        
        if not self.source_path:
            return 'unknown'
        
        ext = self.source_path.suffix.lower()
        if ext == '.json':
            return 'json'
        elif ext == '.pdf':
            return 'pdf'
        elif ext == '.csv':
            return 'csv'
        elif ext == '.txt':
            return 'txt'
        elif ext in ['.docx', '.doc']:
            return 'docx'
        else:
            return 'unknown'
    
    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """Parse the source and return raw data dictionary."""
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the source name for provenance."""
        pass
    
    def validate_source(self) -> bool:
        """Validate that source exists and is accessible."""
        if self._is_url(self.source_path_str):
            return True
        if self.source_path:
            exists = self.source_path.exists() and self.source_path.is_file()
            print(f"Validating source: {self.source_path} - Exists: {exists}")
            return exists
        return False
    
    def get_file_hash(self) -> str:
        """Get hash of the source file for deduplication."""
        if not self.validate_source():
            return ""
        
        try:
            with open(self.source_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""