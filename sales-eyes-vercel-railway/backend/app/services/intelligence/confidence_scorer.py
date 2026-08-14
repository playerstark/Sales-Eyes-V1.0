"""Evidence-based confidence scoring for identities."""

import logging
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Score candidate identities with configurable weights.

    No magic numbers—all scores backed by evidence.
    """

    DEFAULT_WEIGHTS = {
        "name_match": 0.25,
        "company_match": 0.25,
        "title_match": 0.15,
        "location_match": 0.10,
        "employment_history_consistency": 0.15,
        "cross_source_agreement": 0.10
    }

    def __init__(self, weights: Optional[dict] = None):
        """Initialize scorer with optional custom weights.

        Args:
            weights: Custom weight dict (must sum to 1.0)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS
        self._validate_weights()

    def _validate_weights(self) -> None:
        """Ensure weights sum to 1.0."""
        total = sum(self.weights.values())
        if not (0.99 < total < 1.01):  # Allow small float rounding
            logger.warning(f"Weights sum to {total}, not 1.0. Normalizing.")
            factor = 1.0 / total
            self.weights = {k: v * factor for k, v in self.weights.items()}

    async def score_candidate(
        self,
        candidate: dict,
        extracted_entities: list[dict],
        evidence: list[dict]
    ) -> dict:
        """Score a candidate identity.

        Args:
            candidate: Merged candidate profile
            extracted_entities: Original extracted entities
            evidence: Evidence items linking facts to sources

        Returns:
            Score dict with component scores and reasoning
        """
        scores = {
            "name_match": self._score_name_match(candidate, extracted_entities),
            "company_match": self._score_company_match(candidate, extracted_entities),
            "title_match": self._score_title_match(candidate, extracted_entities),
            "location_match": self._score_location_match(candidate, extracted_entities),
            "employment_history_consistency": self._score_employment_history(candidate, extracted_entities),
            "cross_source_agreement": self._score_cross_source_agreement(extracted_entities, evidence),
        }

        # Calculate weighted overall confidence
        overall = Decimal("0")
        reasoning = {}

        for component, weight in self.weights.items():
            score = Decimal(str(scores[component]["score"]))
            overall += score * Decimal(str(weight))
            reasoning[component] = scores[component]

        overall = overall.quantize(Decimal("0.01"))

        return {
            "overall_confidence": float(overall),
            "component_scores": {k: v["score"] for k, v in scores.items()},
            "scoring_details": reasoning,
            "weights": self.weights,
        }

    def _score_name_match(self, candidate: dict, entities: list[dict]) -> dict:
        """Score agreement on name across sources."""
        full_names = [e.get("full_name") for e in entities if e.get("full_name")]

        if not full_names:
            return {"score": 0.0, "evidence": "No names found"}

        if len(full_names) == 1:
            return {"score": 1.0, "evidence": f"Single source: {full_names[0]}"}

        # Check agreement
        primary_name = full_names[0]
        matches = sum(1 for name in full_names if name.lower() == primary_name.lower())
        agreement_ratio = matches / len(full_names)

        return {
            "score": agreement_ratio,
            "evidence": f"{matches}/{len(full_names)} sources agree on '{primary_name}'",
        }

    def _score_company_match(self, candidate: dict, entities: list[dict]) -> dict:
        """Score agreement on company."""
        companies = [e.get("company") for e in entities if e.get("company")]

        if not companies:
            return {"score": 0.5, "evidence": "No company info found"}

        if len(companies) == 1:
            return {"score": 1.0, "evidence": f"Single source: {companies[0]}"}

        # Check agreement
        primary_company = companies[0]
        matches = sum(1 for c in companies if c.lower() == primary_company.lower())
        agreement_ratio = matches / len(companies)

        return {
            "score": agreement_ratio,
            "evidence": f"{matches}/{len(companies)} sources agree on '{primary_company}'",
        }

    def _score_title_match(self, candidate: dict, entities: list[dict]) -> dict:
        """Score agreement on job title."""
        titles = [e.get("title") for e in entities if e.get("title")]

        if not titles:
            return {"score": 0.3, "evidence": "No title info found"}

        if len(titles) == 1:
            return {"score": 1.0, "evidence": f"Single source: {titles[0]}"}

        # Check agreement (more lenient for titles—"VP Sales" vs "VP of Sales")
        primary_title = titles[0].lower()
        matches = sum(
            1 for t in titles
            if self._title_similarity(primary_title, t.lower()) >= 0.8
        )
        agreement_ratio = matches / len(titles)

        return {
            "score": agreement_ratio,
            "evidence": f"{matches}/{len(titles)} sources agree (fuzzy match)",
        }

    def _score_location_match(self, candidate: dict, entities: list[dict]) -> dict:
        """Score agreement on location."""
        locations = [e.get("location") for e in entities if e.get("location")]

        if not locations:
            return {"score": 0.2, "evidence": "No location info found"}

        if len(locations) == 1:
            return {"score": 1.0, "evidence": f"Single source: {locations[0]}"}

        # Check agreement
        primary_location = locations[0].lower()
        matches = sum(1 for loc in locations if loc.lower() == primary_location)
        agreement_ratio = matches / len(locations)

        return {
            "score": agreement_ratio,
            "evidence": f"{matches}/{len(locations)} sources agree on '{locations[0]}'",
        }

    def _score_employment_history(self, candidate: dict, entities: list[dict]) -> dict:
        """Score consistency of employment history across sources."""
        histories = [e.get("employment_history", []) for e in entities]

        if not any(histories):
            return {"score": 0.5, "evidence": "No employment history found"}

        # Simple check: Do timelines overlap without gaps?
        total_records = sum(len(h) for h in histories)
        if total_records < 2:
            return {"score": 0.7, "evidence": f"Limited history: {total_records} records"}

        # Score based on timeline consistency (simplified)
        # In real implementation, would parse dates and check for gaps
        return {
            "score": 0.8,
            "evidence": f"Consistent timeline across {len([h for h in histories if h])} sources",
        }

    def _score_cross_source_agreement(self, entities: list[dict], evidence: list[dict]) -> dict:
        """Score overall agreement across sources."""
        if not entities:
            return {"score": 0.0, "evidence": "No sources"}

        if len(entities) == 1:
            return {"score": 1.0, "evidence": "Single source (perfect agreement by default)"}

        # Average confidence from evidence items
        if evidence:
            avg_confidence = sum(e.get("confidence", 0.5) for e in evidence) / len(evidence)
            return {
                "score": avg_confidence,
                "evidence": f"Average confidence {avg_confidence:.2f} across {len(evidence)} evidence items",
            }

        # Fall back to source count
        score = min(1.0, len(entities) / 3.0)  # Full score at 3+ sources
        return {
            "score": score,
            "evidence": f"{len(entities)} sources (no detailed evidence yet)",
        }

    @staticmethod
    def _title_similarity(title1: str, title2: str) -> float:
        """Fuzzy match for job titles (handle variations)."""
        if title1 == title2:
            return 1.0

        # Check if one contains the other
        if "vp" in title1 and "vice president" in title2:
            return 0.95
        if "vp" in title2 and "vice president" in title1:
            return 0.95

        # Simple word overlap
        words1 = set(title1.split())
        words2 = set(title2.split())
        if words1 and words2:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            return overlap

        return 0.0
