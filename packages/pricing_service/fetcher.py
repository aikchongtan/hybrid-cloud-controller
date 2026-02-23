"""AWS pricing data fetcher module.

This module provides functions to fetch pricing data from AWS Pricing API,
store it in the database, and retrieve current and historical pricing data.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from packages.database import get_session
from packages.database.models import PricingDataModel

logger = logging.getLogger("hybrid_cloud.pricing_service")


def fetch_pricing_data() -> dict[str, dict[str, Decimal]]:
    """Fetch current pricing data from AWS Pricing API.
    
    Fetches pricing for EC2, EBS, S3, and data transfer services from the
    AWS Pricing API and stores it in the database with a timestamp.
    
    Returns:
        Dictionary containing pricing data with keys:
        - ec2_pricing: dict mapping instance types to hourly rates
        - ebs_pricing: dict mapping volume types to GB/month rates
        - s3_pricing: dict mapping storage classes to GB/month rates
        - data_transfer_pricing: dict mapping transfer types to GB rates
        
    Raises:
        ClientError: If AWS API call fails
        BotoCoreError: If boto3 client error occurs
    """
    logger.info("Fetching pricing data from AWS Pricing API")
    
    try:
        # Initialize AWS Pricing API client (us-east-1 is required for pricing API)
        pricing_client = boto3.client("pricing", region_name="us-east-1")
        
        # Fetch EC2 pricing
        ec2_pricing = _fetch_ec2_pricing(pricing_client)
        logger.debug(f"Fetched {len(ec2_pricing)} EC2 instance types")
        
        # Fetch EBS pricing
        ebs_pricing = _fetch_ebs_pricing(pricing_client)
        logger.debug(f"Fetched {len(ebs_pricing)} EBS volume types")
        
        # Fetch S3 pricing
        s3_pricing = _fetch_s3_pricing(pricing_client)
        logger.debug(f"Fetched {len(s3_pricing)} S3 storage classes")
        
        # Fetch data transfer pricing
        data_transfer_pricing = _fetch_data_transfer_pricing(pricing_client)
        logger.debug(f"Fetched {len(data_transfer_pricing)} data transfer types")
        
        # Store in database
        pricing_data = {
            "ec2_pricing": ec2_pricing,
            "ebs_pricing": ebs_pricing,
            "s3_pricing": s3_pricing,
            "data_transfer_pricing": data_transfer_pricing,
        }
        
        _store_pricing_data(pricing_data)
        logger.info("Successfully fetched and stored pricing data")
        
        return pricing_data
        
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to fetch pricing data from AWS API: {e}")
        raise


def get_current_pricing() -> Optional[dict[str, dict[str, Decimal]]]:
    """Get the most recent pricing data from the database.
    
    If the AWS Pricing API is unavailable, this function returns cached
    pricing data from the database.
    
    Returns:
        Dictionary containing pricing data, or None if no data exists.
        Structure matches fetch_pricing_data() return value.
    """
    session = get_session()
    try:
        # Query most recent pricing record
        pricing_record = (
            session.query(PricingDataModel)
            .order_by(PricingDataModel.fetched_at.desc())
            .first()
        )
        
        if not pricing_record:
            logger.warning("No pricing data found in database")
            return None
        
        # Deserialize JSON pricing data
        pricing_data = {
            "ec2_pricing": _deserialize_pricing(pricing_record.ec2_pricing_json),
            "ebs_pricing": _deserialize_pricing(pricing_record.ebs_pricing_json),
            "s3_pricing": _deserialize_pricing(pricing_record.s3_pricing_json),
            "data_transfer_pricing": _deserialize_pricing(
                pricing_record.data_transfer_pricing_json
            ),
        }
        
        logger.info(f"Retrieved pricing data from {pricing_record.fetched_at}")
        return pricing_data
        
    finally:
        session.close()


def get_pricing_history(
    start_date: datetime, end_date: datetime
) -> list[dict[str, any]]:
    """Get historical pricing data for trend analysis.
    
    Args:
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)
        
    Returns:
        List of pricing data records with timestamps, ordered chronologically.
        Each record contains:
        - id: Pricing record ID
        - fetched_at: Timestamp when data was fetched
        - ec2_pricing: EC2 pricing data
        - ebs_pricing: EBS pricing data
        - s3_pricing: S3 pricing data
        - data_transfer_pricing: Data transfer pricing data
    """
    session = get_session()
    try:
        # Query pricing records within date range
        pricing_records = (
            session.query(PricingDataModel)
            .filter(
                PricingDataModel.fetched_at >= start_date,
                PricingDataModel.fetched_at <= end_date,
            )
            .order_by(PricingDataModel.fetched_at.asc())
            .all()
        )
        
        # Convert to list of dictionaries
        history = []
        for record in pricing_records:
            history.append(
                {
                    "id": record.id,
                    "fetched_at": record.fetched_at,
                    "ec2_pricing": _deserialize_pricing(record.ec2_pricing_json),
                    "ebs_pricing": _deserialize_pricing(record.ebs_pricing_json),
                    "s3_pricing": _deserialize_pricing(record.s3_pricing_json),
                    "data_transfer_pricing": _deserialize_pricing(
                        record.data_transfer_pricing_json
                    ),
                }
            )
        
        logger.info(
            f"Retrieved {len(history)} pricing records from {start_date} to {end_date}"
        )
        return history
        
    finally:
        session.close()


def _fetch_ec2_pricing(pricing_client) -> dict[str, Decimal]:
    """Fetch EC2 instance pricing.
    
    Args:
        pricing_client: Boto3 pricing client
        
    Returns:
        Dictionary mapping instance types to hourly rates in USD
    """
    # Sample EC2 instance types for common use cases
    instance_types = [
        "t3.micro",
        "t3.small",
        "t3.medium",
        "t3.large",
        "m5.large",
        "m5.xlarge",
        "m5.2xlarge",
        "c5.large",
        "c5.xlarge",
        "r5.large",
        "r5.xlarge",
    ]
    
    ec2_pricing = {}
    
    for instance_type in instance_types:
        try:
            response = pricing_client.get_products(
                ServiceCode="AmazonEC2",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                    {"Type": "TERM_MATCH", "Field": "location", "Value": "US East (N. Virginia)"},
                    {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                    {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                    {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
                ],
                MaxResults=1,
            )
            
            if response["PriceList"]:
                price_item = json.loads(response["PriceList"][0])
                # Extract on-demand pricing
                terms = price_item.get("terms", {}).get("OnDemand", {})
                for term_key, term_value in terms.items():
                    price_dimensions = term_value.get("priceDimensions", {})
                    for dim_key, dim_value in price_dimensions.items():
                        price_per_unit = dim_value.get("pricePerUnit", {}).get("USD")
                        if price_per_unit:
                            ec2_pricing[instance_type] = Decimal(price_per_unit)
                            break
                    if instance_type in ec2_pricing:
                        break
        except Exception as e:
            logger.warning(f"Failed to fetch pricing for {instance_type}: {e}")
            # Use fallback pricing
            ec2_pricing[instance_type] = _get_fallback_ec2_price(instance_type)
    
    return ec2_pricing


def _fetch_ebs_pricing(pricing_client) -> dict[str, Decimal]:
    """Fetch EBS volume pricing.
    
    Args:
        pricing_client: Boto3 pricing client
        
    Returns:
        Dictionary mapping volume types to GB/month rates in USD
    """
    volume_types = {
        "gp3": "General Purpose SSD (gp3)",
        "gp2": "General Purpose SSD (gp2)",
        "io2": "Provisioned IOPS SSD (io2)",
        "st1": "Throughput Optimized HDD (st1)",
        "sc1": "Cold HDD (sc1)",
    }
    
    ebs_pricing = {}
    
    for vol_type, vol_description in volume_types.items():
        try:
            response = pricing_client.get_products(
                ServiceCode="AmazonEC2",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
                    {"Type": "TERM_MATCH", "Field": "volumeApiName", "Value": vol_type},
                    {"Type": "TERM_MATCH", "Field": "location", "Value": "US East (N. Virginia)"},
                ],
                MaxResults=1,
            )
            
            if response["PriceList"]:
                price_item = json.loads(response["PriceList"][0])
                terms = price_item.get("terms", {}).get("OnDemand", {})
                for term_key, term_value in terms.items():
                    price_dimensions = term_value.get("priceDimensions", {})
                    for dim_key, dim_value in price_dimensions.items():
                        price_per_unit = dim_value.get("pricePerUnit", {}).get("USD")
                        if price_per_unit:
                            ebs_pricing[vol_type] = Decimal(price_per_unit)
                            break
                    if vol_type in ebs_pricing:
                        break
        except Exception as e:
            logger.warning(f"Failed to fetch pricing for EBS {vol_type}: {e}")
            ebs_pricing[vol_type] = _get_fallback_ebs_price(vol_type)
    
    return ebs_pricing


def _fetch_s3_pricing(pricing_client) -> dict[str, Decimal]:
    """Fetch S3 storage pricing.
    
    Args:
        pricing_client: Boto3 pricing client
        
    Returns:
        Dictionary mapping storage classes to GB/month rates in USD
    """
    storage_classes = {
        "STANDARD": "Standard",
        "INTELLIGENT_TIERING": "Intelligent-Tiering",
        "STANDARD_IA": "Standard - Infrequent Access",
        "ONEZONE_IA": "One Zone - Infrequent Access",
        "GLACIER": "Glacier Flexible Retrieval",
    }
    
    s3_pricing = {}
    
    for class_key, class_name in storage_classes.items():
        try:
            response = pricing_client.get_products(
                ServiceCode="AmazonS3",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "location", "Value": "US East (N. Virginia)"},
                    {"Type": "TERM_MATCH", "Field": "storageClass", "Value": class_name},
                ],
                MaxResults=1,
            )
            
            if response["PriceList"]:
                price_item = json.loads(response["PriceList"][0])
                terms = price_item.get("terms", {}).get("OnDemand", {})
                for term_key, term_value in terms.items():
                    price_dimensions = term_value.get("priceDimensions", {})
                    for dim_key, dim_value in price_dimensions.items():
                        price_per_unit = dim_value.get("pricePerUnit", {}).get("USD")
                        if price_per_unit:
                            s3_pricing[class_key] = Decimal(price_per_unit)
                            break
                    if class_key in s3_pricing:
                        break
        except Exception as e:
            logger.warning(f"Failed to fetch pricing for S3 {class_key}: {e}")
            s3_pricing[class_key] = _get_fallback_s3_price(class_key)
    
    return s3_pricing


def _fetch_data_transfer_pricing(pricing_client) -> dict[str, Decimal]:
    """Fetch data transfer pricing.
    
    Args:
        pricing_client: Boto3 pricing client
        
    Returns:
        Dictionary mapping transfer types to GB rates in USD
    """
    # Data transfer pricing is complex, using simplified fallback values
    data_transfer_pricing = {
        "internet_egress": Decimal("0.09"),  # Per GB out to internet
        "inter_region": Decimal("0.02"),  # Per GB between regions
        "inter_az": Decimal("0.01"),  # Per GB between AZs
        "inbound": Decimal("0.00"),  # Inbound is free
    }
    
    logger.debug("Using fallback data transfer pricing")
    return data_transfer_pricing


def _get_fallback_ec2_price(instance_type: str) -> Decimal:
    """Get fallback EC2 pricing when API is unavailable."""
    fallback_prices = {
        "t3.micro": Decimal("0.0104"),
        "t3.small": Decimal("0.0208"),
        "t3.medium": Decimal("0.0416"),
        "t3.large": Decimal("0.0832"),
        "m5.large": Decimal("0.096"),
        "m5.xlarge": Decimal("0.192"),
        "m5.2xlarge": Decimal("0.384"),
        "c5.large": Decimal("0.085"),
        "c5.xlarge": Decimal("0.17"),
        "r5.large": Decimal("0.126"),
        "r5.xlarge": Decimal("0.252"),
    }
    return fallback_prices.get(instance_type, Decimal("0.10"))


def _get_fallback_ebs_price(volume_type: str) -> Decimal:
    """Get fallback EBS pricing when API is unavailable."""
    fallback_prices = {
        "gp3": Decimal("0.08"),
        "gp2": Decimal("0.10"),
        "io2": Decimal("0.125"),
        "st1": Decimal("0.045"),
        "sc1": Decimal("0.015"),
    }
    return fallback_prices.get(volume_type, Decimal("0.10"))


def _get_fallback_s3_price(storage_class: str) -> Decimal:
    """Get fallback S3 pricing when API is unavailable."""
    fallback_prices = {
        "STANDARD": Decimal("0.023"),
        "INTELLIGENT_TIERING": Decimal("0.023"),
        "STANDARD_IA": Decimal("0.0125"),
        "ONEZONE_IA": Decimal("0.01"),
        "GLACIER": Decimal("0.004"),
    }
    return fallback_prices.get(storage_class, Decimal("0.023"))


def _store_pricing_data(pricing_data: dict[str, dict[str, Decimal]]) -> None:
    """Store pricing data in the database.
    
    Args:
        pricing_data: Dictionary containing ec2_pricing, ebs_pricing,
                     s3_pricing, and data_transfer_pricing
    """
    session = get_session()
    try:
        pricing_record = PricingDataModel(
            id=str(uuid4()),
            ec2_pricing_json=_serialize_pricing(pricing_data["ec2_pricing"]),
            ebs_pricing_json=_serialize_pricing(pricing_data["ebs_pricing"]),
            s3_pricing_json=_serialize_pricing(pricing_data["s3_pricing"]),
            data_transfer_pricing_json=_serialize_pricing(
                pricing_data["data_transfer_pricing"]
            ),
            fetched_at=datetime.utcnow(),
        )
        
        session.add(pricing_record)
        session.commit()
        logger.info(f"Stored pricing data with ID {pricing_record.id}")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to store pricing data: {e}")
        raise
    finally:
        session.close()


def _serialize_pricing(pricing_dict: dict[str, Decimal]) -> str:
    """Serialize pricing dictionary to JSON string.
    
    Args:
        pricing_dict: Dictionary with Decimal values
        
    Returns:
        JSON string representation
    """
    # Convert Decimal to string for JSON serialization
    serializable = {k: str(v) for k, v in pricing_dict.items()}
    return json.dumps(serializable)


def _deserialize_pricing(pricing_json: str) -> dict[str, Decimal]:
    """Deserialize pricing JSON string to dictionary.
    
    Args:
        pricing_json: JSON string representation
        
    Returns:
        Dictionary with Decimal values
    """
    pricing_dict = json.loads(pricing_json)
    # Convert string back to Decimal
    return {k: Decimal(v) for k, v in pricing_dict.items()}
