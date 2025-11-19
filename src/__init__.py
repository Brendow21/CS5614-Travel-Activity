"""Real-time Travel Activity Recommendation System"""

from .models import Activity, TravelRecommendation
from .travel_system import RealTimeTravelActivitySystem

__version__ = "1.0.0"
__all__ = ["Activity", "TravelRecommendation", "RealTimeTravelActivitySystem"]