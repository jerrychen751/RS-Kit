# change this later

"""Public API functions for RS-Kit."""

from .core.query import Query

def query(source: str) -> Query:
    """Create a new query for the specified source plugin.
    
    Args:
        source (str): Data source plugin name (e.g., 'nasa_earthdata').
        
    Returns:
        (Query): Query instance for method chaining.
    """
    return Query().from_source(source)