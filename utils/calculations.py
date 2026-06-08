from typing import Optional


def calculate_average_price(prices: list[float]) -> Optional[float]:
    """
    Calculate the average price from a list of prices.
    Returns None if the list is empty.
    """
    if not prices:
        return None
    return round(sum(prices) / len(prices), 2)


def format_rate(value: Optional[float]) -> str:
    """Format a rate value for display, handling None gracefully."""
    if value is None:
        return "N/A"
    return f"{value:,.2f}"
