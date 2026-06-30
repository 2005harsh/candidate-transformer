"""Normalization utilities for candidate data.

Provides `Normalizer` to canonicalize phones, emails, dates, countries,
skills, locations, and full candidate records.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser
import phonenumbers

try:
    import pycountry  # optional
except Exception:
    pycountry = None

from app.core.config import get_settings


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class Normalizer:
    # Small fallback validation set, only used when pycountry isn't
    # installed, so we never invent a country code for arbitrary 2-letter
    # garbage (e.g. "XX") just because it happens to look like a code.
    _FALLBACK_ALPHA2 = {
        "US", "GB", "CA", "AU", "IN", "DE", "FR", "ES", "IT", "NL", "SE",
        "CH", "SG", "JP", "CN", "BR", "MX", "ZA", "AE", "IE", "NZ", "PL",
    }

    def __init__(self, settings=None, default_region: str = "US") -> None:
        self.settings = settings or get_settings()
        self.skill_map = {k.lower(): v for k, v in (self.settings.SKILL_SYNONYMS or {}).items()}
        self.default_region = default_region

    def normalize_phone(self, phone: str, region: Optional[str] = None) -> Optional[str]:
        if not phone:
            return None
        region = region or self.default_region
        try:
            num = phonenumbers.parse(phone, region)
            if not phonenumbers.is_possible_number(num) and not phonenumbers.is_valid_number(num):
                return None
            return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            return None

    def normalize_email(self, email: str) -> Optional[str]:
        if not email:
            return None
        e = email.strip().lower()
        if EMAIL_RE.match(e):
            return e
        return None

    def normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        try:
            dt = date_parser.parse(date_str, fuzzy=True, default=None)
            # If year-only, dateutil may parse as Jan 1; detect numeric year
            year_only = False
            if re.fullmatch(r"\d{4}", date_str.strip()):
                year_only = True

            if year_only:
                return dt.strftime("%Y")
            # return YYYY-MM
            return dt.strftime("%Y-%m")
        except Exception:
            return None

    def normalize_country(self, country: Optional[str]) -> Optional[str]:
        if not country:
            return None
        c = country.strip()
        # If already an alpha-2 code, validate it against a real reference
        # instead of blindly trusting any two-letter string (e.g. "XX").
        if len(c) == 2 and c.isalpha():
            code = c.upper()
            if pycountry:
                try:
                    if pycountry.countries.get(alpha_2=code):
                        return code
                except Exception:
                    pass
            elif code in self._FALLBACK_ALPHA2:
                return code
            # Unrecognized 2-letter code: don't invent a value, fall through
            # to fuzzy/name-based lookup below in case it's coincidentally
            # also a valid prefix, otherwise return None.

        # Try pycountry if available
        if pycountry:
            try:
                res = pycountry.countries.search_fuzzy(c)
                if res:
                    return res[0].alpha_2
            except Exception:
                pass

        # common mapping fallback
        common = {
            "united states": "US",
            "usa": "US",
            "us": "US",
            "united kingdom": "GB",
            "uk": "GB",
            "great britain": "GB",
            "germany": "DE",
            "france": "FR",
            "canada": "CA",
            "australia": "AU",
            "india": "IN",
        }
        key = c.lower()
        if key in common:
            return common[key]

        return None

    def canonicalize_skill(self, skill: Any) -> Any:
        """Map a skill (string or dict) to canonical name using `SKILL_SYNONYMS`.

        If `skill` is a dict with a `name` field, update it in-place and return the dict.
        Otherwise returns the canonical string.
        """
        if not skill:
            return skill
        if isinstance(skill, dict):
            name = skill.get("name") or skill.get("skill")
            if not name:
                return skill
            canon = self.skill_map.get(str(name).lower())
            if canon:
                skill["name"] = canon
            else:
                skill["name"] = str(name).strip()
            return skill

        s = str(skill).strip()
        return self.skill_map.get(s.lower(), s)

    def normalize_location(self, location: Optional[Dict[str, Optional[str]]]) -> Dict[str, Optional[str]]:
        if not location:
            return {"city": None, "region": None, "country": None}
        city = (location.get("city") or location.get("locality") or "").strip() or None
        region = (location.get("region") or location.get("state") or "").strip() or None
        country = (location.get("country") or "").strip() or None
        country_code = self.normalize_country(country) if country else None
        return {"city": city, "region": region, "country": country_code}

    def normalize_record(self, record: Dict[str, Any], default_phone_region: Optional[str] = None) -> Dict[str, Any]:
        """Normalize an entire candidate record in-place and return it.

        Fields normalized: `emails`, `phones`, `skills`, `experience` (dates),
        `education` (dates), and `location`.
        """
        rec = dict(record)  # shallow copy

        # Location (normalized first so its country can inform phone parsing)
        loc = rec.get("location")
        rec["location"] = self.normalize_location(loc)

        # Emails
        emails = rec.get("emails") or []
        norm_emails = []
        for e in emails:
            ne = self.normalize_email(e)
            if ne and ne not in norm_emails:
                norm_emails.append(ne)
        rec["emails"] = norm_emails

        # Phones — prefer a region hint derived from the candidate's own
        # location over the hardcoded default, so e.g. a 10-digit Indian
        # number isn't silently mis-parsed as a US number just because no
        # explicit region was passed in.
        phones = rec.get("phones") or []
        norm_phones = []
        region = default_phone_region or (rec["location"] or {}).get("country") or self.default_region
        for p in phones:
            np = self.normalize_phone(p, region)
            if np and np not in norm_phones:
                norm_phones.append(np)
        rec["phones"] = norm_phones

        # Skills
        skills = rec.get("skills") or []
        norm_skills = []
        for s in skills:
            cs = self.canonicalize_skill(s)
            # if dict, use name field for dedupe
            key = cs["name"] if isinstance(cs, dict) else cs
            if key and key not in [x["name"] if isinstance(x, dict) else x for x in norm_skills]:
                norm_skills.append(cs)
        rec["skills"] = norm_skills

        # Experience: normalize start/end dates
        exp = rec.get("experience") or []
        norm_exp = []
        for e in exp:
            if not isinstance(e, dict):
                norm_exp.append(e)
                continue
            ne = dict(e)
            ne["start"] = self.normalize_date(ne.get("start"))
            ne["end"] = self.normalize_date(ne.get("end"))
            norm_exp.append(ne)
        rec["experience"] = norm_exp

        # Education: normalize end_year or dates
        edu = rec.get("education") or []
        norm_edu = []
        for ed in edu:
            if not isinstance(ed, dict):
                norm_edu.append(ed)
                continue
            ned = dict(ed)
            # try to normalize end_year if present as string/date
            ey = ned.get("end_year")
            if ey:
                try:
                    # if numeric year
                    if isinstance(ey, int):
                        ned["end_year"] = int(ey)
                    else:
                        parsed = date_parser.parse(str(ey), fuzzy=True)
                        ned["end_year"] = int(parsed.year)
                except Exception:
                    ned["end_year"] = None
            norm_edu.append(ned)
        rec["education"] = norm_edu

        return rec
