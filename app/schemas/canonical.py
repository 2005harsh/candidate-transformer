"""Canonical Pydantic schemas for candidate records."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, Field, HttpUrl


class Location(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


class Link(BaseModel):
    type: Optional[str] = None
    url: Optional[HttpUrl] = None


class Skill(BaseModel):
    name: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)


class Experience(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    summary: Optional[str] = None
    sources: List[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None
    sources: List[str] = Field(default_factory=list)


class ProvenanceEntry(BaseModel):
    field: str
    source: str
    method: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Any] = None


class CanonicalRecord(BaseModel):
    candidate_id: Optional[str] = None
    full_name: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    location: Optional[Location] = None
    links: List[Link] = Field(default_factory=list)
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[Skill] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    provenance: List[ProvenanceEntry] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    def add_provenance(self, field: str, source: str, method: Optional[str] = None, timestamp: Optional[datetime] = None, details: Optional[Any] = None) -> None:
        """Append a provenance entry for a given field."""

        entry = ProvenanceEntry(
            field=field,
            source=source,
            method=method,
            timestamp=timestamp or datetime.utcnow(),
            details=details,
        )
        self.provenance.append(entry)

    def update_confidence(self) -> float:
        """Recalculate and set `overall_confidence` based on skill confidences.

        Current implementation: mean of all skill confidences (0..1). If no
        skills are present, `overall_confidence` remains 0.0.
        """

        if not self.skills:
            self.overall_confidence = 0.0
            return self.overall_confidence

        avg = sum(s.confidence for s in self.skills) / len(self.skills)
        # clamp to [0,1]
        self.overall_confidence = max(0.0, min(1.0, float(avg)))
        return self.overall_confidence
