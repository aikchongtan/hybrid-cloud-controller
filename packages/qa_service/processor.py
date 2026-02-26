"""Q&A processor for answering questions about TCO analysis.

This module processes user questions in the context of TCO analysis results,
providing explanations, comparisons, and recommendations.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class CostLineItem:
    """Individual cost line item in a breakdown."""

    category: str
    description: str
    amount: Decimal
    unit: str


@dataclass
class CostBreakdown:
    """Complete cost breakdown with itemized line items."""

    items: list[CostLineItem]
    total: Decimal
    currency: str = "USD"


@dataclass
class Configuration:
    """Configuration data for TCO context."""

    cpu_cores: int
    memory_gb: int
    instance_count: int
    storage_type: str
    storage_capacity_gb: int
    storage_iops: Optional[int]
    bandwidth_mbps: int
    monthly_data_transfer_gb: int
    utilization_percentage: int
    operating_hours_per_month: int


@dataclass
class TCOContext:
    """Context for Q&A processing containing TCO analysis data."""

    configuration: Configuration
    on_prem_costs: dict[int, CostBreakdown]  # years -> breakdown
    aws_costs: dict[int, CostBreakdown]  # years -> breakdown


def process_question(question: str, context: TCOContext) -> str:
    """
    Process user question in the context of TCO analysis.

    This is the main entry point for Q&A processing. It analyzes the question
    and routes it to the appropriate handler (cost item explanation, comparison,
    or recommendation).

    Args:
        question: User's question text
        context: TCO context with configuration and cost breakdowns

    Returns:
        Response string answering the user's question
    """
    question_lower = question.lower().strip()

    # Check for cost item explanation requests
    if any(
        keyword in question_lower
        for keyword in ["what is", "explain", "tell me about", "cost of"]
    ):
        # Extract potential cost item name
        for breakdown in [*context.on_prem_costs.values(), *context.aws_costs.values()]:
            for item in breakdown.items:
                if item.category.lower() in question_lower:
                    return get_cost_item_explanation(item.category, context)

    # Check for comparison requests
    if any(
        keyword in question_lower
        for keyword in ["compare", "difference", "versus", "vs", "between"]
    ):
        # Extract aspect to compare
        aspects = ["power", "hardware", "ec2", "ebs", "s3", "data transfer", "cooling", "maintenance"]
        for aspect in aspects:
            if aspect in question_lower:
                return compare_aspects(aspect, context)

    # Check for recommendation requests
    if any(
        keyword in question_lower
        for keyword in ["recommend", "suggestion", "should i", "which", "better"]
    ):
        return generate_recommendation(context)

    # Default response for unrecognized questions
    return (
        "I can help you understand your TCO analysis. You can ask me to:\n"
        "- Explain specific cost items (e.g., 'What is the EC2 cost?')\n"
        "- Compare aspects between on-premises and AWS (e.g., 'Compare power costs')\n"
        "- Get recommendations based on your workload (e.g., 'Which option should I choose?')"
    )


def get_cost_item_explanation(item_name: str, context: TCOContext) -> str:
    """
    Explain a specific cost line item from the TCO breakdown.

    Args:
        item_name: Name of the cost item (e.g., "EC2", "Hardware", "Power")
        context: TCO context with configuration and cost breakdowns

    Returns:
        Explanation string with item details and costs across time periods
    """
    item_name_lower = item_name.lower()
    
    # Search for the item in both on-prem and AWS costs
    on_prem_items = {}
    aws_items = {}
    
    for years, breakdown in context.on_prem_costs.items():
        for item in breakdown.items:
            if item.category.lower() == item_name_lower:
                on_prem_items[years] = item
                break
    
    for years, breakdown in context.aws_costs.items():
        for item in breakdown.items:
            if item.category.lower() == item_name_lower:
                aws_items[years] = item
                break
    
    # Build explanation based on what we found
    if on_prem_items:
        item = on_prem_items[1]  # Use 1-year for description
        response = f"**{item.category}** (On-Premises)\n\n"
        response += f"{item.description}\n\n"
        response += "Costs over time:\n"
        for years in sorted(on_prem_items.keys()):
            response += f"- {years} year(s): ${on_prem_items[years].amount:,.2f}\n"
        return response
    
    if aws_items:
        item = aws_items[1]  # Use 1-year for description
        response = f"**{item.category}** (AWS)\n\n"
        response += f"{item.description}\n\n"
        response += "Costs over time:\n"
        for years in sorted(aws_items.keys()):
            response += f"- {years} year(s): ${aws_items[years].amount:,.2f}\n"
        return response
    
    return f"I couldn't find information about '{item_name}' in your TCO analysis."


def compare_aspects(aspect: str, context: TCOContext) -> str:
    """
    Compare a specific aspect between on-premises and AWS costs.

    Args:
        aspect: Aspect to compare (e.g., "power", "storage", "data transfer")
        context: TCO context with configuration and cost breakdowns

    Returns:
        Comparison string showing costs for both options
    """
    aspect_lower = aspect.lower()
    
    # Find matching items in both breakdowns (using 1-year for comparison)
    on_prem_breakdown = context.on_prem_costs.get(1)
    aws_breakdown = context.aws_costs.get(1)
    
    if not on_prem_breakdown or not aws_breakdown:
        return "Unable to compare - cost data is incomplete."
    
    on_prem_item = None
    aws_item = None
    
    # Search for matching items
    for item in on_prem_breakdown.items:
        if aspect_lower in item.category.lower():
            on_prem_item = item
            break
    
    for item in aws_breakdown.items:
        if aspect_lower in item.category.lower():
            aws_item = item
            break
    
    # Build comparison response
    if on_prem_item and aws_item:
        response = f"**Comparing {aspect.title()} Costs** (1-year period)\n\n"
        response += f"On-Premises: ${on_prem_item.amount:,.2f}\n"
        response += f"  {on_prem_item.description}\n\n"
        response += f"AWS: ${aws_item.amount:,.2f}\n"
        response += f"  {aws_item.description}\n\n"
        
        difference = on_prem_item.amount - aws_item.amount
        if difference > 0:
            response += f"On-premises is ${difference:,.2f} more expensive than AWS for {aspect}."
        elif difference < 0:
            response += f"AWS is ${abs(difference):,.2f} more expensive than on-premises for {aspect}."
        else:
            response += f"Both options have the same {aspect} cost."
        
        return response
    
    if on_prem_item:
        return f"Found {aspect} in on-premises costs (${on_prem_item.amount:,.2f}), but not in AWS costs."
    
    if aws_item:
        return f"Found {aspect} in AWS costs (${aws_item.amount:,.2f}), but not in on-premises costs."
    
    return f"I couldn't find '{aspect}' in either on-premises or AWS cost breakdowns."


def generate_recommendation(context: TCOContext) -> str:
    """
    Generate a recommendation based on the workload profile and TCO analysis.

    This function analyzes the configuration and cost comparison to provide
    a recommendation on which cloud path might be more suitable.

    Args:
        context: TCO context with configuration and cost breakdowns

    Returns:
        Recommendation string based on workload characteristics and costs
    """
    config = context.configuration
    
    # Get 3-year totals for comparison (most common planning horizon)
    on_prem_total = context.on_prem_costs[3].total
    aws_total = context.aws_costs[3].total
    
    # Calculate cost difference
    cost_difference = on_prem_total - aws_total
    cost_difference_percent = (abs(cost_difference) / on_prem_total) * 100
    
    # Analyze workload characteristics
    is_high_utilization = config.utilization_percentage >= 70
    is_always_on = config.operating_hours_per_month >= 600  # ~20 hours/day
    is_large_scale = config.instance_count >= 10
    
    # Build recommendation
    response = "**Recommendation Based on Your Workload**\n\n"
    
    # Cost comparison
    if abs(cost_difference_percent) < 10:
        response += f"The 3-year TCO is similar for both options (within {cost_difference_percent:.1f}%):\n"
        response += f"- On-Premises: ${on_prem_total:,.2f}\n"
        response += f"- AWS: ${aws_total:,.2f}\n\n"
    elif cost_difference > 0:
        response += f"AWS is ${abs(cost_difference):,.2f} ({cost_difference_percent:.1f}%) cheaper over 3 years:\n"
        response += f"- On-Premises: ${on_prem_total:,.2f}\n"
        response += f"- AWS: ${aws_total:,.2f}\n\n"
    else:
        response += f"On-Premises is ${abs(cost_difference):,.2f} ({cost_difference_percent:.1f}%) cheaper over 3 years:\n"
        response += f"- On-Premises: ${on_prem_total:,.2f}\n"
        response += f"- AWS: ${aws_total:,.2f}\n\n"
    
    # Workload-based recommendation
    response += "**Workload Analysis:**\n"
    
    if is_high_utilization and is_always_on:
        response += (
            f"- Your workload has high utilization ({config.utilization_percentage}%) "
            f"and runs continuously ({config.operating_hours_per_month} hours/month)\n"
            "- This profile typically benefits from on-premises infrastructure where "
            "you pay fixed costs regardless of usage\n"
        )
    elif not is_high_utilization or not is_always_on:
        response += (
            f"- Your workload has variable usage ({config.utilization_percentage}% utilization, "
            f"{config.operating_hours_per_month} hours/month)\n"
            "- This profile typically benefits from AWS where you pay only for what you use\n"
        )
    
    if is_large_scale:
        response += (
            f"- You're running {config.instance_count} instances, which is a significant scale\n"
            "- At this scale, on-premises infrastructure can offer better economies of scale\n"
        )
    
    # Final recommendation
    response += "\n**Suggested Path:**\n"
    
    if is_high_utilization and is_always_on and (cost_difference > 0 or abs(cost_difference_percent) < 10):
        response += (
            "Consider **On-Premises** for your steady-state, high-utilization workload. "
            "The fixed costs are offset by consistent usage, and you'll have more control over your infrastructure."
        )
    elif not is_high_utilization or not is_always_on:
        response += (
            "Consider **AWS** for your variable workload. "
            "You'll benefit from pay-as-you-go pricing and can scale resources up or down as needed."
        )
    elif cost_difference < -on_prem_total * Decimal("0.2"):  # AWS is 20%+ more expensive
        response += (
            "Consider **On-Premises** given the significant cost savings over 3 years. "
            "However, factor in the operational overhead of managing your own infrastructure."
        )
    else:
        response += (
            "Both options are viable. Consider **AWS** if you value flexibility and managed services, "
            "or **On-Premises** if you prefer control and have existing infrastructure expertise."
        )
    
    return response
