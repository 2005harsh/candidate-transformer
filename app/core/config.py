"""Configuration settings for Candidate Transformer.

Defines a `Settings` class using pydantic-settings.
"""

from typing import List, Optional, Dict

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration and defaults.

    Environment variables may be used to override any of these values when
    running the application (depending on your pydantic-settings configuration).
    """

    inputs: List[str] = Field(default_factory=list)
    config: Optional[str] = None
    output: str = "output.json"
    debug: bool = False
    log_level: str = "INFO"

    # Confidence weights
    ATS_WEIGHT: float = 1.0
    RESUME_WEIGHT: float = 0.8
    RECRUITER_WEIGHT: float = 0.7
    GITHUB_WEIGHT: float = 0.6
    NOTES_WEIGHT: float = 0.5

    FUZZY_NAME_THRESHOLD: int = 90

    SKILL_SYNONYMS: Dict[str, str] = Field(default_factory=lambda: {
        "python": "Python",
        "py": "Python",
        "javascript": "JavaScript",
        "js": "JavaScript",
        "typescript": "TypeScript",
        "ts": "TypeScript",
        "java": "Java",
        "csharp": "C#",
        "c#": "C#",
        "golang": "Go",
        "go": "Go",
        "sql": "SQL",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "aws": "AWS",
        "gcp": "GCP",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
    })

    class Config:
        env_prefix = "CT_"


def get_settings() -> Settings:
    """Return application settings (instantiates from environment)."""

    return Settings()
