from typing import Dict, Any, Optional
from ..schemas.canonical import CanonicalRecord


class ProjectionEngine:
    """Dynamic projection layer for transforming canonical records."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config or {}
        self.options = self.config.get('options', {}) if isinstance(self.config.get('options', {}), dict) else {}
        self.default_missing = self.options.get('missing', self.config.get('missing', 'null'))
        self.fields = self._normalize_fields(self.config)
        self.include_provenance = self.options.get('include_provenance', self.config.get('include_provenance', True))
        self.include_confidence = self.options.get('include_confidence', self.config.get('include_confidence', True))

    def _normalize_fields(self, config: Dict[str, Any]) -> list[Dict[str, Any]]:
        """Normalize config into a single internal field list format."""
        fields = config.get('fields', [])
        if isinstance(fields, list) and fields:
            return [self._normalize_field_definition(field) for field in fields]

        mapping = config.get('mapping', {})
        if isinstance(mapping, dict) and mapping:
            normalized_fields = []
            for output_field, source in mapping.items():
                if isinstance(source, dict):
                    field_config = dict(source)
                    field_config['path'] = field_config.get('path', output_field)
                    field_config['from'] = field_config.get('from', field_config.get('path'))
                else:
                    field_config = {'path': output_field, 'from': source}

                normalized_fields.append(self._normalize_field_definition(field_config))
            return normalized_fields

        return []

    def _normalize_field_definition(self, field_config: Any) -> Dict[str, Any]:
        """Ensure field definitions are dictionaries with standard keys."""
        if not isinstance(field_config, dict):
            return {'path': str(field_config), 'from': str(field_config)}

        normalized = dict(field_config)
        path = normalized.get('path')
        if not path:
            path = normalized.get('output')
        if not path:
            path = normalized.get('name')
        normalized['path'] = path
        normalized['from'] = normalized.get('from', path)
        normalized['required'] = normalized.get('required', False)
        normalized['on_missing'] = normalized.get('on_missing', self.default_missing)
        normalized['type'] = normalized.get('type')
        normalized['normalize'] = normalized.get('normalize')
        return normalized
    
    def project(self, record: CanonicalRecord) -> Dict[str, Any]:
        """Project canonical record to output schema based on config."""
        # If no field configs, use default schema
        if not self.fields:
            return self._default_projection(record)
        
        result = {}
        
        # Apply each field configuration
        for field_config in self.fields:
            path = field_config.get('path')
            from_path = field_config.get('from', path)
            required = field_config.get('required', False)
            on_missing = field_config.get('on_missing', self.default_missing)
            field_type = field_config.get('type')
            normalize = field_config.get('normalize')
            
            # Get value from canonical record
            value = self._get_nested_value(record, from_path)
            
            # Handle missing values
            if value is None:
                if on_missing == 'null':
                    result[path] = None
                elif on_missing == 'omit':
                    continue
                elif on_missing == 'error':
                    raise ValueError(f"Required field missing: {path}")
                continue
            
            # Apply normalization if specified
            if normalize:
                value = self._apply_normalization(value, normalize)

            # Convert Pydantic sub-models (Skill, Experience, Education, ...)
            # to plain dicts/lists so the output is always clean JSON, even
            # when no explicit `type` was requested in the field config.
            value = self._to_jsonable(value)

            # Transform based on type
            result[path] = self._transform_value(value, field_type)
        
        # Add provenance if requested
        if self.include_provenance and record.provenance:
            result['_provenance'] = [
                {'field': p.field, 'source': p.source, 'method': p.method}
                for p in record.provenance
            ]
        
        # Add confidence if requested
        if self.include_confidence:
            result['_confidence'] = record.overall_confidence
        
        return result
    
    def _default_projection(self, record: CanonicalRecord) -> Dict[str, Any]:
        """Project using default schema."""
        result = {
            'candidate_id': record.candidate_id,
            'full_name': record.full_name,
            'emails': record.emails if record.emails else [],
            'phones': record.phones if record.phones else [],
            'headline': record.headline,
            'years_experience': record.years_experience,
            'skills': [s.dict() for s in record.skills] if record.skills else [],
            'experience': [e.dict() for e in record.experience] if record.experience else [],
            'education': [e.dict() for e in record.education] if record.education else [],
            'location': record.location.dict() if record.location else None,
            'links': [l.dict() for l in record.links] if record.links else [],
        }
        
        # Add provenance and confidence
        if record.provenance:
            result['provenance'] = [p.dict() for p in record.provenance]
        result['overall_confidence'] = record.overall_confidence
        
        # Remove None values for clean output
        return {k: v for k, v in result.items() if v is not None}
    
    def _to_jsonable(self, value: Any) -> Any:
        """Recursively convert Pydantic models (and lists of them) to plain
        dicts/lists so downstream JSON serialization never falls back to
        Python repr() strings for objects like Skill, Experience, etc."""
        if isinstance(value, list):
            return [self._to_jsonable(v) for v in value]
        if isinstance(value, dict):
            return {k: self._to_jsonable(v) for k, v in value.items()}
        if hasattr(value, 'dict') and callable(getattr(value, 'dict', None)):
            return value.dict()
        return value

    def _get_nested_value(self, record: CanonicalRecord, path: str) -> Any:
        """Get value from record using dot notation path."""
        if not path:
            return None
        
        # Handle array indexing like emails[0]
        import re
        array_match = re.match(r'^([a-zA-Z_]+)\[(\d+)\]$', path)
        if array_match:
            field = array_match.group(1)
            index = int(array_match.group(2))
            if hasattr(record, field):
                value = getattr(record, field)
                if isinstance(value, list) and index < len(value):
                    return value[index]
                return None
        
        # Regular dot notation
        parts = path.split('.')
        current = record
        
        for part in parts:
            if part.isdigit():
                idx = int(part)
                if isinstance(current, list) and idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                if hasattr(current, part):
                    current = getattr(current, part)
                elif isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
        
        return current
    
    def _apply_normalization(self, value: Any, normalize: str) -> Any:
        """Apply normalization to a value."""
        from .normalizer import Normalizer
        normalizer = Normalizer()
        
        if normalize == 'E164':
            # Phone normalization
            if isinstance(value, list):
                return [normalizer.normalize_phone(str(v)) for v in value if v]
            else:
                return normalizer.normalize_phone(str(value))
        elif normalize == 'canonical':
            # Skill canonicalization
            if isinstance(value, list):
                return [normalizer.canonicalize_skill(str(v)) for v in value if v]
            else:
                return normalizer.canonicalize_skill(str(value))
        elif normalize == 'date':
            # Date normalization
            if isinstance(value, list):
                return [normalizer.normalize_date(str(v)) for v in value if v]
            else:
                return normalizer.normalize_date(str(value))
        else:
            return value
    
    def _transform_value(self, value: Any, field_type: Optional[str]) -> Any:
        """Transform value based on field type."""
        if field_type == 'string':
            return str(value) if value is not None else None
        elif field_type == 'number':
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        elif field_type == 'integer':
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        elif field_type == 'boolean':
            return bool(value)
        elif field_type == 'object':
            # Keep as is for nested objects
            if hasattr(value, 'dict'):
                return value.dict()
            elif isinstance(value, dict):
                return value
            else:
                return value
        elif field_type == 'string[]' or field_type == 'array':
            if isinstance(value, list):
                return [v if isinstance(v, (dict, list)) else str(v) for v in value if v is not None]
            return []
        else:
            return value

    _TYPE_MAP = {
        'string': str,
        'number': (int, float),
        'integer': int,
        'boolean': bool,
        'object': dict,
        'array': list,
        'string[]': list,
    }

    def get_output_schema(self) -> Dict[str, Any]:
        """Build a validation schema matching whatever shape `project()`
        will actually produce, for either the default schema or a custom
        runtime config, so output can be validated before it's returned."""
        if not self.fields:
            return {
                'candidate_id': str,
                'full_name': str,
                'emails': [str],
                'phones': [str],
                'location': {'city': str, 'region': str, 'country': str},
                'links': list,
                'headline': str,
                'years_experience': (int, float),
                'skills': list,
                'experience': list,
                'education': list,
                'provenance': list,
                'overall_confidence': (int, float),
            }

        schema: Dict[str, Any] = {}
        for field_config in self.fields:
            path = field_config.get('path')
            field_type = field_config.get('type')
            schema[path] = self._TYPE_MAP.get(field_type)  # None if untyped/unrecognized
        return schema

    def get_required_fields(self) -> list[str]:
        """Output field names marked `required: true` in the config."""
        if not self.fields:
            return []
        return [f['path'] for f in self.fields if f.get('required')]