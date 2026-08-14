"""Detect contradictions across sources for a candidate."""

import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ConflictDetector:
    """Detect and surface contradictions in a candidate profile."""

    CRITICAL_FIELDS = ["full_name", "company", "title", "location"]
    SIMILARITY_THRESHOLD = 0.85

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    async def detect_conflicts(
        self,
        candidate: dict,
        extracted_entities: list[dict],
        evidence: list[dict]
    ) -> list[dict]:
        """Detect contradictions across sources.

        Args:
            candidate: Merged candidate profile
            extracted_entities: Original extracted entities
            evidence: Evidence items

        Returns:
            List of conflict records [{conflict_type, field_name, value_a, value_b, ...}, ...]
        """
        conflicts = []

        # Check critical fields for contradictions
        for field in self.CRITICAL_FIELDS:
            field_conflicts = self._find_conflicts_in_field(
                field, extracted_entities, evidence
            )
            conflicts.extend(field_conflicts)

        logger.info(f"Found {len(conflicts)} conflicts in candidate")
        return conflicts

    def _find_conflicts_in_field(
        self,
        field: str,
        entities: list[dict],
        evidence: list[dict]
    ) -> list[dict]:
        """Find conflicts for a specific field."""
        conflicts = []

        # Get all values for this field
        values = []
        for i, entity in enumerate(entities):
            value = entity.get(field)
            if value:
                values.append({
                    "value": str(value),
                    "source_index": i,
                    "entity_idx": i
                })

        # Check for contradictions
        if len(values) < 2:
            return []  # No conflict if only one or zero sources

        # Compare each pair of values
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                value_a = values[i]["value"].lower()
                value_b = values[j]["value"].lower()

                # Exact match or high similarity = no conflict
                if value_a == value_b:
                    continue

                similarity = self._string_similarity(value_a, value_b)
                if similarity >= self.similarity_threshold:
                    continue  # Similar enough, not a real conflict

                # We have a conflict!
                # Find source URLs for this evidence
                source_a_url = self._find_source_url_for_entity(
                    values[i]["entity_idx"], evidence, field
                )
                source_b_url = self._find_source_url_for_entity(
                    values[j]["entity_idx"], evidence, field
                )

                conflict = {
                    "conflict_type": self._classify_conflict_type(field, value_a, value_b),
                    "field_name": field,
                    "value_a": values[i]["value"],
                    "value_b": values[j]["value"],
                    "source_a_url": source_a_url or "unknown",
                    "source_b_url": source_b_url or "unknown",
                    "severity": self._calculate_severity(field, value_a, value_b),
                    "resolution": None,
                    "detected_at": datetime.utcnow().isoformat(),
                }

                conflicts.append(conflict)

        return conflicts

    @staticmethod
    def _string_similarity(s1: str, s2: str) -> float:
        """Calculate string similarity (0.0 to 1.0)."""
        if s1 == s2:
            return 1.0

        # Check if one contains the other
        if s1 in s2 or s2 in s1:
            return 0.9

        # Simple overlap-based similarity
        words1 = set(s1.split())
        words2 = set(s2.split())

        if words1 and words2:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            return overlap

        return 0.0

    @staticmethod
    def _classify_conflict_type(field: str, value_a: str, value_b: str) -> str:
        """Classify the type of conflict."""
        if field == "full_name":
            return "name_mismatch"
        elif field == "company":
            return "company_change"
        elif field == "title":
            return "title_change"
        elif field == "location":
            return "location_change"
        else:
            return "field_mismatch"

    @staticmethod
    def _calculate_severity(field: str, value_a: str, value_b: str) -> str:
        """Calculate severity: high | medium | low."""
        # Name conflicts are high severity
        if field == "full_name":
            return "high"

        # Company conflicts are high severity
        if field == "company":
            return "high"

        # Title and location are medium
        return "medium"

    @staticmethod
    def _find_source_url_for_entity(entity_idx: int, evidence: list[dict], field: str) -> Optional[str]:
        """Find source URL for an entity and field."""
        # This is a simplified lookup; in real implementation,
        # would maintain a mapping of entity_idx -> source_url
        for ev in evidence:
            if ev.get("fact_type") == field:
                urls = ev.get("source_urls", [])
                if urls:
                    return urls[0]
        return None


class ConflictResolver:
    """Provide utilities for resolving conflicts."""

    @staticmethod
    def suggest_resolution(conflict: dict) -> str:
        """Suggest which value to prefer."""
        # Simple heuristic: longer strings often more complete
        value_a = conflict.get("value_a", "")
        value_b = conflict.get("value_b", "")

        if len(value_a) > len(value_b):
            return value_a
        elif len(value_b) > len(value_a):
            return value_b

        # Default: alphabetical
        return min(value_a, value_b)

    @staticmethod
    def mark_resolved(conflict: dict, resolution: str, resolved_value: str) -> dict:
        """Mark conflict as resolved.

        Args:
            conflict: Original conflict dict
            resolution: 'accept_a' | 'accept_b' | 'custom'
            resolved_value: The chosen value

        Returns:
            Updated conflict dict
        """
        conflict["resolution"] = resolution
        conflict["resolved_value"] = resolved_value
        conflict["resolved_at"] = datetime.utcnow().isoformat()
        return conflict
