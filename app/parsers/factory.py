from typing import Optional
from pathlib import Path
from .base import BaseParser
from .json_parser import JSONParser
from .pdf_parser import PDFParser
from .csv_parser import CSVParser
from .txt_parser import TXTParser
from .docx_parser import DOCXParser
from .github_parser import GitHubParser


class ParserFactory:
    """Factory for creating appropriate parsers based on source type."""
    
    @staticmethod
    def create_parser(source_path: str) -> Optional[BaseParser]:
        """Create a parser for the given source."""
        print(f"Creating parser for: {source_path}")
        
        # Check if it's a URL
        if source_path.startswith(('http://', 'https://')):
            if 'github.com' in source_path:
                print("Detected GitHub URL")
                return GitHubParser(source_path)
            elif 'linkedin.com' in source_path:
                print("LinkedIn parser not implemented")
                return None
            else:
                print(f"Unsupported URL: {source_path}")
                return None
        
        # Check if file exists
        path = Path(source_path)
        if not path.exists():
            print(f"File not found: {source_path}")
            return None
        
        ext = path.suffix.lower()
        print(f"File extension: {ext}")
        
        if ext == '.json':
            return JSONParser(source_path)
        elif ext == '.pdf':
            return PDFParser(source_path)
        elif ext == '.csv':
            return CSVParser(source_path)
        elif ext == '.txt':
            return TXTParser(source_path)
        elif ext in ['.docx', '.doc']:
            return DOCXParser(source_path)
        else:
            print(f"Unsupported file type: {ext}")
            return None