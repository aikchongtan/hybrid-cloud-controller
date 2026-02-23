"""Pricing service package for AWS pricing data management.

This package provides functionality to fetch, store, and retrieve AWS pricing
data from the AWS Pricing API.
"""

from packages.pricing_service import fetcher

__all__ = ["fetcher"]
