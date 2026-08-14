"""Identity resolution service for reconciling extracted entities."""

import logging
from typing import Optional
from difflib import SequenceMatcher
from decimal import Decimal

from app.models.intelligence import (
    ExtractedEntity as ExtractedEntityModel, CandidateIdentity, Evidence
)
from app.services.intelligence.interfaces import ExtractedEntity

logger = logging.getLogger(__name__)


class StringMatcher:
    """String similarity matching using multiple algorithms."""

    @staticmethod
    def levenshtein_similarity(s1: str, s2: str) -> float:
        """Levenshtein distance similarity (0.0 to 1.0)."""
        if not s1 or not s2:
            return 0.0
        if s1.lower() == s2.lower():
            return 1.0

        s1_lower = s1.lower()
        s2_lower = s2.lower()

        # If one contains the other, high similarity
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return 0.85

        # Levenshtein distance
        matcher = SequenceMatcher(None, s1_lower, s2_lower)
        ratio = matcher.ratio()
        return ratio

    @staticmethod
    def fuzzy_match(s1: str, s2: str) -> float:
        """Fuzzy matching (handles typos, abbreviations)."""
        if not s1 or not s2:
            return 0.0

        s1_lower = s1.lower().strip()
        s2_lower = s2.lower().strip()

        if s1_lower == s2_lower:
            return 1.0

        # Check for partial matches (first/last names)
        s1_parts = set(s1_lower.split())
        s2_parts = set(s2_lower.split())

        if s1_parts and s2_parts:
            overlap = len(s1_parts & s2_parts)
            max_len = max(len(s1_parts), len(s2_parts))
            if overlap > 0:
                return overlap / max_len

        # Fall back to Levenshtein
        return StringMatcher.levenshtein_similarity(s1, s2)

    @staticmethod
    def should_match(s1: Optional[str], s2: Optional[str], threshold: float = 0.85) -> bool:
        """Check if two strings should be considered a match."""
        if not s1 or not s2:
            return False

        similarity = StringMatcher.levenshtein_similarity(s1, s2)
        return similarity >= threshold


class IdentityResolution:
    """Resolve multiple extracted entities into candidate identities."""

    def __init__(self, name_threshold: float = 0.85, company_threshold: float = 0.80):
        self.name_threshold = name_threshold
        self.company_threshold = company_threshold

    async def resolve_entities(
        self,
        entities: list[ExtractedEntity],
        session_id: str
    ) -> list[dict]:
        """Resolve multiple entities into candidate identities.

        Args:
            entities: List of extracted entities
            session_id: Intelligence session ID

        Returns:
            List of candidate identity dicts with merged data
        """
        if not entities:
            return []

        logger.info(f"Resolving {len(entities)} entities into candidates")

        # Group entities by similarity
        candidates = []
        used_indices = set()

        for i, entity in enumerate(entities):
            if i in used_indices:
                continue

            # Start a new candidate with this entity
            entity_group = [entity]
            used_indices.add(i)

            # Find similar entities
            for j, other in enumerate(entities):
                if j <= i or j in used_indices:
                    continue

                if self._entities_match(entity, other):
                    entity_group.append(other)
                    used_indices.add(j)

            # Merge group into single candidate
            candidate = self._merge_entities(entity_group)
            candidates.append(candidate)

        logger.info(f"Resolved into {len(candidates)} candidates")
        return candidates

    def _entities_match(self, entity1: ExtractedEntity, entity2: ExtractedEntity) -> bool:
        """Check if two entities represent the same person/company."""
        if entity1.entity_type != entity2.entity_type:
            return False

        # Match on name
        if entity1.full_name and entity2.full_name:
            name_match = StringMatcher.should_match(
                entity1.full_name, entity2.full_name, self.name_threshold
            )
            if not name_match:
                return False

        # Match on company (if both have)
        if entity1.company and entity2.company:
            company_match = StringMatcher.should_match(
                entity1.company, entity2.company, self.company_threshold
            )
            if not company_match:
                return False

        # If we have name match, consider it the same person
        return True

    def _merge_entities(self, entities: list[ExtractedEntity]) -> dict:
        """Merge multiple entities into a single candidate profile.

        Strategy: Take best values from each entity, preferring non-None values.
        """
        if not entities:
            return {}

        # Start with first entity
        primary = entities[0]

        merged = {
            "full_name": primary.full_name,
            "first_name": primary.first_name,
            "last_name": primary.last_name,
            "title": primary.title,
            "company": primary.company,
            "location": primary.location,
            "email": primary.email,
            "phone": primary.phone,
            "linkedin_url": primary.linkedin_url,
            "skills": list(set(primary.skills)) if primary.skills else [],
            "employment_history": primary.employment_history or [],
            "education": primary.education or [],
            "social_profiles": primary.social_profiles or {},
            "source_count": len(entities),
            "source_entities": [self._entity_to_dict(e) for e in entities],
        }

        # Merge in additional entities
        for entity in entities[1:]:
            # Prefer non-None values
            merged["full_name"] = merged["full_name"] or entity.full_name
            merged["first_name"] = merged["first_name"] or entity.first_name
            merged["last_name"] = merged["last_name"] or entity.last_name
            merged["title"] = merged["title"] or entity.title
            merged["company"] = merged["company"] or entity.company
            merged["location"] = merged["location"] or entity.location
            merged["email"] = merged["email"] or entity.email
            merged["phone"] = merged["phone"] or entity.phone
            merged["linkedin_url"] = merged["linkedin_url"] or entity.linkedin_url

            # Merge lists
            if entity.skills:
                merged["skills"] = list(set(merged["skills"] + entity.skills))
            if entity.employment_history:
                merged["employment_history"].extend(entity.employment_history)
            if entity.education:
                merged["education"].extend(entity.education)
            if entity.social_profiles:
                merged["social_profiles"].update(entity.social_profiles)

        return merged

    @staticmethod
    def _entity_to_dict(entity: ExtractedEntity) -> dict:
        """Convert ExtractedEntity to dict."""
        return {
            "full_name": entity.full_name,
            "title": entity.title,
            "company": entity.company,
            "email": entity.email,
            "linkedin_url": entity.linkedin_url,
            "extraction_method": getattr(entity, "extraction_method", "unknown"),
            "extraction_confidence": getattr(entity, "extraction_confidence", None),
        }


class IdentityMatcher:
    """Match extracted entities to build evidence graph."""

    def __init__(self):
        self.string_matcher = StringMatcher()

    async def link_evidence(
        self,
        candidate: dict,
        extracted_entities: list[ExtractedEntity],
        sources: list[dict]
    ) -> list[dict]:
        """Link facts to source evidence.

        Args:
            candidate: Merged candidate profile
            extracted_entities: Original entities
            sources: Source information [{url, title}, ...]

        Returns:
            List of evidence records [{fact_type, fact_value, source_url, confidence}, ...]
        """
        evidence = []

        # Link each fact to its sources
        fact_fields = [
            "full_name", "first_name", "last_name", "title", "company",
            "location", "email", "phone", "linkedin_url"
        ]

        for field in fact_fields:
            value = candidate.get(field)
            if not value:
                continue

            # Find which entities contributed this fact
            confidence_sum = 0.0
            source_urls = []

            for i, entity in enumerate(extracted_entities):
                entity_value = getattr(entity, field, None)
                if entity_value:
                    # Check if this entity's value matches the candidate's
                    similarity = self.string_matcher.levenshtein_similarity(
                        str(value), str(entity_value)
                    )
                    if similarity >= 0.85:
                        confidence_sum += similarity
                        if i < len(sources):
                            source_urls.append(sources[i].get("url", ""))

            if source_urls:
                avg_confidence = Decimal(str(confidence_sum / len(source_urls)))
                avg_confidence = avg_confidence.quantize(Decimal("0.01"))

                evidence.append({
                    "fact_type": field,
                    "fact_value": str(value),
                    "source_urls": list(set(source_urls)),  # Deduplicate
                    "confidence": float(avg_confidence),
                })

        logger.info(f"Linked {len(evidence)} evidence items for candidate")
        return evidence
