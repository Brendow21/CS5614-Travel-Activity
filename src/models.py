

"""Data models for the travel activity system"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class Activity:
    """Data structure representing a single travel activity or point of interest."""
    
    place_id: str
    name: str
    address: str
    location: Dict[str, float]  # {"lat": ..., "lng": ...}
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    types: List[str] = field(default_factory=list)
    opening_hours: Optional[Dict] = None
    price_level: Optional[int] = None
    photos: List[str] = field(default_factory=list)
    reviews: List[Dict] = field(default_factory=list)
    distance: Optional[float] = None  # Distance from the user (in meters)
    
    def to_dict(self) -> Dict:
        """Convert the Activity object into a serializable dictionary."""
        return {
            "place_id": self.place_id,
            "name": self.name,
            "address": self.address,
            "location": self.location,
            "rating": self.rating,
            "user_ratings_total": self.user_ratings_total,
            "types": self.types,
            "opening_hours": self.opening_hours,
            "price_level": self.price_level,
            "photos": self.photos,
            "reviews": self.reviews,
            "distance": self.distance
        }
    
    def is_open_now(self) -> bool:
        """Return True if the place is currently open based on Google Maps metadata."""
        if self.opening_hours:
            return self.opening_hours.get("open_now", False)
        return False
    
    def get_price_symbol(self) -> str:
        """Return a human-readable price level symbol (e.g., $, $$, $$$)."""
        if self.price_level:
            return "$" * self.price_level
        return "N/A"


@dataclass
class TravelRecommendation:
    """Container for aggregated travel recommendation results."""
    
    activities: List[Activity]
    total_count: int
    search_location: Dict[str, float]
    timestamp: str
    query_info: Optional[Dict] = None  # Additional metadata about the search/query
    
    def to_dict(self) -> Dict:
        """Convert the TravelRecommendation object into a serializable dictionary."""
        return {
            "activities": [a.to_dict() for a in self.activities],
            "total_count": self.total_count,
            "search_location": self.search_location,
            "timestamp": self.timestamp,
            "query_info": self.query_info
        }
    
    def get_top_rated(self, n: int = 5) -> List[Activity]:
        """Return the top-N activities sorted by rating and review count."""
        sorted_activities = sorted(
            self.activities,
            key=lambda x: (x.rating or 0, x.user_ratings_total or 0),
            reverse=True
        )
        return sorted_activities[:n]
    
    def filter_by_type(self, activity_type: str) -> List[Activity]:
        """Return all activities whose type list contains the specified activity_type."""
        return [a for a in self.activities if activity_type in a.types]

