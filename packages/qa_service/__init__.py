"""Q&A service for conversational assistance about TCO analysis.

This package provides conversational Q&A processing to help users understand
their TCO analysis results, compare costs, and get recommendations.
"""

from packages.qa_service.processor import (
    process_question,
    get_cost_item_explanation,
    compare_aspects,
    generate_recommendation,
)

__all__ = [
    "process_question",
    "get_cost_item_explanation",
    "compare_aspects",
    "generate_recommendation",
]
