"""Unit tests for the travel activity system"""

import os
import pytest
from src.travel_system import RealTimeTravelActivitySystem
from src.models import Activity, TravelRecommendation
from src.utils import calculate_haversine_distance, validate_location, format_distance


@pytest.fixture
def api_key():
    """Get API key from environment"""
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        pytest.skip("GOOGLE_API_KEY not set")
    return key


@pytest.fixture
def system(api_key):
    """Create system instance"""
    return RealTimeTravelActivitySystem(api_key=api_key)


class TestUtils:
    """Test utility functions"""
    
    def test_validate_location_valid(self):
        """Test valid location"""
        assert validate_location({"lat": 35.6762, "lng": 139.6503})
    
    def test_validate_location_invalid(self):
        """Test invalid locations"""
        assert not validate_location({"lat": 200, "lng": 100})  # Invalid range
        assert not validate_location({"lat": 35.6762})  # Missing lng
        assert not validate_location("not a dict")  # Wrong type
    
    def test_haversine_distance(self):
        """Test distance calculation"""
        tokyo = {"lat": 35.6762, "lng": 139.6503}
        osaka = {"lat": 34.6937, "lng": 135.5023}
        
        distance = calculate_haversine_distance(tokyo, osaka)
        
        # Distance should be approximately 400km
        assert 390000 < distance < 410000
    
    def test_format_distance(self):
        """Test distance formatting"""
        assert format_distance(500) == "500m"
        assert format_distance(1500) == "1.50km"
        assert format_distance(10000) == "10.00km"


class TestGeocoding:
    """Test geocoding functionality"""
    
    def test_geocode_valid_location(self, system):
        """Test geocoding a valid location"""
        location = system.geocode_location("Paris, France")
        
        assert location is not None
        assert "lat" in location
        assert "lng" in location
        assert 48 < location["lat"] < 49  # Paris latitude
        assert 2 < location["lng"] < 3    # Paris longitude
    
    def test_geocode_invalid_location(self, system):
        """Test geocoding an invalid location"""
        location = system.geocode_location("XYZ123456789NotAPlace")
        
        assert location is None


class TestSearch:
    """Test activity search functionality"""
    
    def test_search_nearby_activities(self, system):
        """Test searching for nearby activities"""
        location = {"lat": 35.6762, "lng": 139.6503}  # Tokyo
        
        activities = system.search_nearby_activities(
            location=location,
            activity_type="tourist_attraction",
            radius=5000,
            max_results=5
        )
        
        assert len(activities) > 0
        assert all(isinstance(a, Activity) for a in activities)
        assert all(a.place_id for a in activities)
        assert all(a.name for a in activities)
    
    def test_search_with_invalid_location(self, system):
        """Test search with invalid location"""
        activities = system.search_nearby_activities(
            location={"lat": 200, "lng": 300},  # Invalid
            activity_type="restaurant"
        )
        
        assert activities == []


class TestRecommendation:
    """Test recommendation system"""
    
    def test_recommend_activities(self, system):
        """Test full recommendation flow"""
        recommendation = system.recommend_activities(
            location_query="New York, NY",
            activity_types=["tourist_attraction", "museum"],
            radius=5000,
            max_per_type=5
        )
        
        assert isinstance(recommendation, TravelRecommendation)
        assert recommendation.total_count > 0
        assert len(recommendation.activities) > 0
        assert recommendation.search_location
        assert recommendation.timestamp
    
    def test_recommend_with_sorting(self, system):
        """Test recommendation with different sorting"""
        # Test rating sort
        rec_rating = system.recommend_activities(
            location_query="London, UK",
            activity_types=["restaurant"],
            sort_by="rating",
            max_per_type=10
        )
        
        # Check descending rating order
        ratings = [a.rating for a in rec_rating.activities if a.rating]
        assert ratings == sorted(ratings, reverse=True)


class TestRoutePlanning:
    """Test route planning"""
    
    def test_plan_route(self, system):
        """Test route planning"""
        # Get some activities
        recommendation = system.recommend_activities(
            location_query="San Francisco, CA",
            activity_types=["tourist_attraction"],
            max_per_type=5
        )
        
        if recommendation.activities:
            route = system.plan_route(
                activities=recommendation.activities,
                start=recommendation.search_location
            )
            
            assert len(route) == len(recommendation.activities)
            assert all(isinstance(a, Activity) for a in route)


class TestPersonalization:
    """Test personalized recommendations"""
    
    def test_personalized_recommend(self, system):
        """Test personalized recommendation"""
        # Get activities
        recommendation = system.recommend_activities(
            location_query="Paris, France",
            activity_types=["museum", "restaurant", "park"],
            max_per_type=5
        )
        
        if recommendation.activities:
            user_preferences = {
                "museum": 0.9,
                "restaurant": 0.5,
                "park": 0.3
            }
            
            personalized = system.personalized_recommend(
                user_preferences=user_preferences,
                activities=recommendation.activities
            )
            
            assert len(personalized) == len(recommendation.activities)

