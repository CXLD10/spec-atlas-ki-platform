"""Answer provenance extraction and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spec_atlas.answer.engine import Answer
    from spec_atlas.retrieve.descent import Context


@dataclass
class Provenance:
    """Provenance for a single claim."""

    file: str
    start_line: int
    end_line: int
    confidence: float  # 1.0 if validated, 0.7 if ungrounded


class AnswerProvenanceExtractor:
    """Extract and validate provenance from answers."""

    @staticmethod
    def extract_and_validate(
        answer: Answer,
        context: Context,
    ) -> tuple[str, list[Provenance], float]:
        """Extract provenance from answer and validate against context.

        Args:
            answer: Generated Answer object.
            context: Retrieved context (contains validated source spans).

        Returns:
            Tuple of (cleaned_answer_text, validated_provenance_list, overall_confidence).
        """
        validated_provenance = []
        ungrounded_count = 0

        for claim in answer.claims:
            # Parse claim source (file:line format)
            source = claim.source.strip()

            # Try to match against context spans
            is_grounded = False
            for span in context.source_spans:
                span_file = span.get("file", "")
                span_start = span.get("start_line", 0)

                # Simple matching: check if file and line match
                if ":" in source:
                    source_file, source_line_str = source.rsplit(":", 1)
                    try:
                        source_line = int(source_line_str)
                        if source_file in span_file and source_line == span_start:
                            is_grounded = True
                            # Create grounded provenance
                            prov = Provenance(
                                file=span_file,
                                start_line=span.get("start_line", 0),
                                end_line=span.get("end_line", span.get("start_line", 0)),
                                confidence=1.0,
                            )
                            validated_provenance.append(prov)
                            break
                    except ValueError:
                        pass

            if not is_grounded and source:
                # Ungrounded claim: include with lower confidence
                ungrounded_count += 1
                prov = Provenance(
                    file=source,
                    start_line=0,
                    end_line=0,
                    confidence=0.7,
                )
                validated_provenance.append(prov)

        # Calculate overall confidence
        total_claims = len(answer.claims)
        if total_claims > 0:
            grounded_count = len(validated_provenance) - ungrounded_count
            confidence = grounded_count / total_claims
        else:
            confidence = 1.0

        return answer.text, validated_provenance, confidence
