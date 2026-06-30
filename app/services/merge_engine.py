import hashlib
from typing import List, Dict, Any, Optional, Tuple
from rapidfuzz import fuzz
from .normalizer import Normalizer
from ..schemas.canonical import CanonicalRecord, Skill, Experience, Education, Location, Link


class MergeEngine:
    def __init__(self):
        self.normalizer = Normalizer()
        self.source_weights = {
            'ats': 1.0,
            'json': 1.0,
            'resume': 0.8,
            'pdf': 0.8,
            'recruiter': 0.7,
            'csv': 0.7,
            'github': 0.6,
            'notes': 0.5,
            'txt': 0.5
        }
    
    def merge(self, sources: List[Dict[str, Any]]) -> Any:
        """Merge source records into one canonical record per candidate cluster.

        The method returns a list of CanonicalRecord objects for multi-candidate input,
        but preserves backward compatibility by returning a single CanonicalRecord when
        the input is a single logical candidate.
        """
        if not sources:
            return CanonicalRecord()

        clustered_sources = self._cluster_sources(sources)
        merged_records: List[CanonicalRecord] = []

        for group in clustered_sources:
            record = CanonicalRecord()
            group.sort(key=lambda x: self._get_source_weight(x.get('_source', '')), reverse=True)

            for source in group:
                self._merge_source(record, source)

            record.update_confidence()
            self._assign_candidate_id(record)
            merged_records.append(record)

        if len(merged_records) == 1:
            return merged_records[0]
        return merged_records
    
    def _cluster_sources(self, sources: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Cluster source records into candidate groups using deterministic matching rules."""
        groups: List[List[Dict[str, Any]]] = []
        for source in sources:
            matched_group = None
            for group in groups:
                if self._same_candidate(group[0], source):
                    matched_group = group
                    break

            if matched_group is None:
                groups.append([source])
            else:
                matched_group.append(source)

        return groups

    def _same_candidate(self, left: Dict[str, Any], right: Dict[str, Any]) -> bool:
        """Return True when two source records likely belong to the same candidate."""
        left_emails = self._normalize_string_list(left.get('emails') or left.get('email'))
        right_emails = self._normalize_string_list(right.get('emails') or right.get('email'))
        if left_emails and right_emails and set(left_emails) & set(right_emails):
            return True

        left_phones = self._normalize_string_list(left.get('phones') or left.get('phone'))
        right_phones = self._normalize_string_list(right.get('phones') or right.get('phone'))
        left_name = self._normalize_name(left.get('full_name') or left.get('name'))
        right_name = self._normalize_name(right.get('full_name') or right.get('name'))

        if left_phones and right_phones and set(left_phones) & set(right_phones):
            if left_name and right_name and fuzz.ratio(left_name, right_name) >= 95:
                return True

        if left_name and right_name:
            if fuzz.ratio(left_name, right_name) >= 95:
                return True

            if len(left_name.split()) >= 2 and len(right_name.split()) >= 2:
                left_last = left_name.split()[-1]
                right_last = right_name.split()[-1]
                left_initial = left_name.split()[0][0] if left_name.split()[0] else ""
                right_initial = right_name.split()[0][0] if right_name.split()[0] else ""
                if left_last and right_last and left_last == right_last and left_initial == right_initial:
                    return True

        # Preserve backward compatibility when the sources do not contain enough identity signals.
        if not left_emails and not right_emails and not left_phones and not right_phones and not left_name and not right_name:
            return True

        return False

    def _normalize_string_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [self.normalizer.normalize_email(value)] if '@' in value else [value]
        if isinstance(value, list):
            normalized = []
            for item in value:
                if not item:
                    continue
                if isinstance(item, str):
                    normalized.append(self.normalizer.normalize_email(item) if '@' in item else item)
            return normalized
        return []

    def _normalize_name(self, value: Any) -> Optional[str]:
        if not value:
            return None
        return str(value).strip().lower()

    def _assign_candidate_id(self, record: CanonicalRecord) -> None:
        if record.candidate_id:
            return

        email = record.emails[0] if record.emails else ""
        phone = record.phones[0] if record.phones else ""
        name = record.full_name or ""

        if email or phone or name:
            seed = f"{email}|{phone}|{name}".strip("|")
        else:
            seed = "unknown"

        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
        record.candidate_id = f"CAND-{digest}"

    def _get_source_weight(self, source_name: str) -> float:
        """Get weight for a source."""
        source_lower = source_name.lower()
        for key, weight in self.source_weights.items():
            if key in source_lower:
                return weight
        return 0.5
    
    def _merge_source(self, record: CanonicalRecord, source: Dict[str, Any]):
        """Merge a source into the canonical record."""
        source_name = source.get('_source', 'unknown')
        method = source.get('_method', 'parse')
        
        # String fields
        string_fields = ['full_name', 'headline']
        for field in string_fields:
            if field in source and source[field]:
                value = str(source[field]).strip()
                if value:
                    current = getattr(record, field)
                    if not current:
                        setattr(record, field, value)
                        record.add_provenance(field, source_name, method)
        
        # List fields (emails, phones)
        list_fields = ['emails', 'phones']
        for field in list_fields:
            if field in source:
                values = source[field]
                if isinstance(values, str):
                    values = [values]
                elif not isinstance(values, list):
                    continue
                
                current = getattr(record, field)
                for value in values:
                    if value and value not in current:
                        current.append(value)
                        record.add_provenance(field, source_name, method)
        
        # Location
        if 'location' in source and source['location']:
            location_data = source['location']
            if isinstance(location_data, dict):
                if not record.location:
                    record.location = Location(**location_data)
                    record.add_provenance('location', source_name, method)
                else:
                    # Merge location fields
                    for field in ['city', 'region', 'country']:
                        if field in location_data and location_data[field]:
                            if not getattr(record.location, field):
                                setattr(record.location, field, location_data[field])
        
        # Links
        if 'links' in source and source['links']:
            links_data = source['links']
            if isinstance(links_data, list):
                for link in links_data:
                    if isinstance(link, dict) and 'type' in link and 'url' in link:
                        existing = [l for l in record.links if l.type == link['type']]
                        if not existing:
                            record.links.append(Link(**link))
                            record.add_provenance('links', source_name, method)
        
        # Skills
        if 'skills' in source and source['skills']:
            skills_data = source['skills']
            if isinstance(skills_data, list):
                for skill in skills_data:
                    if isinstance(skill, dict) and skill.get('name'):
                        skill_name = self.normalizer.canonicalize_skill(skill['name'])
                        if skill_name:
                            existing = [s for s in record.skills if s.name == skill_name]
                            if existing:
                                if source_name not in existing[0].sources:
                                    existing[0].sources.append(source_name)
                            else:
                                record.skills.append(Skill(
                                    name=skill_name,
                                    confidence=skill.get('confidence', 0.5),
                                    sources=[source_name]
                                ))
                                record.add_provenance(f'skill.{skill_name}', source_name, method)
        
        # Experience
        if 'experience' in source and source['experience']:
            exp_data = source['experience']
            if isinstance(exp_data, list):
                for exp in exp_data:
                    if isinstance(exp, dict) and exp.get('company'):
                        existing = [e for e in record.experience if e.company == exp['company']]
                        if existing:
                            # Update existing
                            for field in ['title', 'start', 'end', 'summary']:
                                if field in exp and exp[field]:
                                    if not getattr(existing[0], field):
                                        setattr(existing[0], field, exp[field])
                            if source_name not in existing[0].sources:
                                existing[0].sources.append(source_name)
                        else:
                            record.experience.append(Experience(
                                company=exp['company'],
                                title=exp.get('title', ''),
                                start=self.normalizer.normalize_date(exp.get('start')),
                                end=self.normalizer.normalize_date(exp.get('end')),
                                summary=exp.get('summary', ''),
                                sources=[source_name]
                            ))
                            record.add_provenance('experience', source_name, method)
        
        # Education - FIXED: Added proper import and handling
        if 'education' in source and source['education']:
            edu_data = source['education']
            if isinstance(edu_data, list):
                for edu in edu_data:
                    if isinstance(edu, dict) and edu.get('institution'):
                        existing = [e for e in record.education if e.institution == edu['institution']]
                        if existing:
                            # Update existing
                            for field in ['degree', 'field', 'end_year']:
                                if field in edu and edu[field]:
                                    if not getattr(existing[0], field):
                                        setattr(existing[0], field, edu[field])
                            if source_name not in existing[0].sources:
                                existing[0].sources.append(source_name)
                        else:
                            # Create new Education object with all fields
                            edu_obj = Education(
                                institution=edu['institution'],
                                degree=edu.get('degree', ''),
                                field=edu.get('field', ''),
                                end_year=edu.get('end_year'),
                                sources=[source_name]
                            )
                            record.education.append(edu_obj)
                            record.add_provenance('education', source_name, method)
        
        # Years experience
        if source.get('years_experience'):
            try:
                years = float(source['years_experience'])
                if not record.years_experience or years > record.years_experience:
                    record.years_experience = years
                    record.add_provenance('years_experience', source_name, method)
            except:
                pass