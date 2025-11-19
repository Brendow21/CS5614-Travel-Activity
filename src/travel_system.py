"""Real-time Travel Activity Recommendation System"""

import os
import yaml
import requests
import logging
import json 
from typing import List, Dict, Optional
from datetime import datetime
from functools import lru_cache

from .models import Activity, TravelRecommendation
from .utils import rate_limit, retry_on_failure, calculate_haversine_distance, validate_location

logger = logging.getLogger(__name__)


class RealTimeTravelActivitySystem:
    
    
    def __init__(self, api_key: str, config_path: Optional[str] = None):
        """
        Args:
            api_key: Google API Key
            config_path ）
        """
        self.api_key = api_key
        
        # Load configuration
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            # Default configuration
            self.config = {
                'google_api': {
                    'rate_limit': 10,
                    'timeout': 10,
                    'batch_size': 25
                },
                'search_defaults': {
                    'radius': 5000,
                    'max_results': 20
                }
            }
        
        # API endpoints
        self.geocode_base_url  = "https://maps.googleapis.com/maps/api/geocode/json"
        self.places_base_url   = "https://maps.googleapis.com/maps/api/place"
        self.distance_base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"

        logger.info("Travel Activity System initialized")
    
    @lru_cache(maxsize=100)
    @retry_on_failure(max_retries=3)
    @rate_limit(calls_per_second=10)
    def geocode_location(self, location_name: str) -> Optional[Dict[str, float]]:
        """
        translate location name to lat/lng
        
        Args:
            location_name
        Returns:
            {"lat": ..., "lng": ...} or None
        """
        url = self.geocode_base_url
        params = {
            "address": location_name,
            "key": self.api_key
        }
        
        timeout = self.config['google_api']['timeout']
        
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            status = data.get("status")
            
            if status == "ZERO_RESULTS":
                logger.warning(f"Location not found: {location_name}")
                return None
            elif status == "OVER_QUERY_LIMIT":
                logger.error("API quota exceeded")
                return None
            elif status == "REQUEST_DENIED":
                logger.error("API request denied - check your API key")
                return None
            elif status != "OK":
                logger.error(f"Geocoding API error: {status}")
                return None
            
            if data.get("results"):
                location = data["results"][0]["geometry"]["location"]
                result = {"lat": location["lat"], "lng": location["lng"]}
                logger.info(f"Geocoded '{location_name}' to {result}")
                return result
        
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for location: {location_name}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in geocode_location: {e}")
        
        return None
    
    @retry_on_failure(max_retries=2)
    @rate_limit(calls_per_second=10)
    def search_nearby_activities(
        self,
        location: Dict[str, float],
        activity_type: str = "tourist_attraction",
        radius: int = 5000,
        max_results: int = 20
    ) -> List[Activity]:
        """
        
        searching for nearby travel activities
        
        Args:
            location: {"lat": ..., "lng": ...}
            activity_type: activity type string
            radius: radius in meters
            max_results: max number of results to return
        
        Returns:
            Activity list
        """
        if not validate_location(location):
            logger.error(f"Invalid location: {location}")
            return []
        
        url = f"{self.places_base_url}/nearbysearch/json"
        params = {
            "location": f"{location['lat']},{location['lng']}",
            "radius": radius,
            "type": activity_type,
            "key": self.api_key
        }
        
        activities = []
        timeout = self.config['google_api']['timeout']
        
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK":
                logger.warning(f"Search API returned status: {data.get('status')}")
                return activities
            
            results = data.get("results", [])[:max_results]
            logger.info(f"Found {len(results)} activities of type '{activity_type}'")
            
            for place in results:
                try:
                    activity = Activity(
                        place_id=place.get("place_id", ""),
                        name=place.get("name", "Unknown"),
                        address=place.get("vicinity", ""),
                        location={
                            "lat": place["geometry"]["location"]["lat"],
                            "lng": place["geometry"]["location"]["lng"]
                        },
                        rating=place.get("rating"),
                        user_ratings_total=place.get("user_ratings_total"),
                        types=place.get("types", []),
                        opening_hours=place.get("opening_hours"),
                        price_level=place.get("price_level"),
                    )
                    
                    # Get photo URLs
                    if "photos" in place:
                        for photo in place["photos"][:3]:
                            photo_url = self._get_photo_url(photo["photo_reference"])
                            activity.photos.append(photo_url)
                    
                    activities.append(activity)
                
                except Exception as e:
                    logger.warning(f"Error parsing activity: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Search error: {e}")
        
        return activities
    
    @retry_on_failure(max_retries=2)
    @rate_limit(calls_per_second=5)
    def get_place_details(self, place_id: str) -> Optional[Activity]:
        """
        get detailed info including reviews
        Args:
            place_id: Google Place ID
        
        Returns:
            whole Activity object
        """
        url = f"{self.places_base_url}/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,rating,formatted_address,geometry,opening_hours,price_level,reviews,photos,types,user_ratings_total",
            "key": self.api_key
        }
        
        timeout = self.config['google_api']['timeout']
        
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK":
                logger.warning(f"Details API returned status: {data.get('status')}")
                return None
            
            result = data["result"]
            
            activity = Activity(
                place_id=place_id,
                name=result.get("name", "Unknown"),
                address=result.get("formatted_address", ""),
                location={
                    "lat": result["geometry"]["location"]["lat"],
                    "lng": result["geometry"]["location"]["lng"]
                },
                rating=result.get("rating"),
                user_ratings_total=result.get("user_ratings_total"),
                types=result.get("types", []),
                opening_hours=result.get("opening_hours"),
                price_level=result.get("price_level"),
            )
            
            # Add photos
            if "photos" in result:
                for photo in result["photos"][:5]:
                    photo_url = self._get_photo_url(photo["photo_reference"])
                    activity.photos.append(photo_url)
            
            # Add reviews
            if "reviews" in result:
                for review in result["reviews"][:5]:
                    activity.reviews.append({
                        "author": review.get("author_name", "Anonymous"),
                        "rating": review.get("rating"),
                        "text": review.get("text", ""),
                        "time": review.get("time")
                    })
            
            logger.info(f"Retrieved details for: {activity.name}")
            return activity
        
        except Exception as e:
            logger.error(f"Details error: {e}")
        
        return None
    
    @retry_on_failure(max_retries=2)
    @rate_limit(calls_per_second=10)
    def calculate_distances(
        self,
        origin: Dict[str, float],
        activities: List[Activity]
       ) -> List[Activity]:
        """
        compute distances from origin to each activity in activities
        Args:
            origin: user location {"lat": ..., "lng": ...}
            activities: Activity list
        
        Returns:
            updated distance string in each Activity,
        """
        if not activities or not validate_location(origin):
            return activities
        
        batch_size = self.config['google_api']['batch_size']
        timeout = self.config['google_api']['timeout']
        
        for i in range(0, len(activities), batch_size):
            batch = activities[i:i + batch_size]
            destinations = [
                f"{a.location['lat']},{a.location['lng']}" 
                for a in batch
            ]
            
            url = self.distance_base_url
            params = {
                "origins": f"{origin['lat']},{origin['lng']}",
                "destinations": "|".join(destinations),
                "key": self.api_key
            }
            
            try:
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") != "OK":
                    logger.warning(f"Distance API batch {i//batch_size + 1} status: {data.get('status')}")
                    continue
                
                elements = data["rows"][0]["elements"]
                
                for j, element in enumerate(elements):
                    if element.get("status") == "OK":
                        activities[i + j].distance = element["distance"]["value"]
                
                logger.debug(f"Calculated distances for batch {i//batch_size + 1}")
            
            except Exception as e:
                logger.error(f"Distance calculation error (batch {i//batch_size + 1}): {e}")
        
        return activities
    
    def _get_photo_url(self, photo_reference: str, max_width: int = 400) -> str:
        """Construct photo URL from photo reference"""
        return f"{self.places_base_url}/photo?maxwidth={max_width}&photoreference={photo_reference}&key={self.api_key}"
    
    def recommend_activities(
        self,
        location_query: str,
        activity_types: Optional[List[str]] = None,
        radius: int = 5000,
        max_per_type: int = 10,
        sort_by: str = "rating"
    ) -> TravelRecommendation:
        """
        whole recommendation pipeline
        Args:
            location_query: location name
            activity_types: activity type list
            radius: radius in meters
            max_per_type: every type max results
            sort_by: sorted by ("rating", "distance", "reviews")
        
        Returns:
            TravelRecommendation object
        """
        if activity_types is None:
            activity_types = ["tourist_attraction"]
        
        logger.info(f"Starting recommendation for: {location_query}")
        
        # Geocode location
        location = self.geocode_location(location_query)
        if not location:
            logger.error(f"Unable to geocode location: {location_query}")
            return TravelRecommendation(
                activities=[],
                total_count=0,
                search_location={},
                timestamp=datetime.now().isoformat(),
                query_info={
                    "query": location_query,
                    "error": "Location not found"
                }
            )
        
        # Search activities
        all_activities = []
        for activity_type in activity_types:
            activities = self.search_nearby_activities(
                location=location,
                activity_type=activity_type,
                radius=radius,
                max_results=max_per_type
            )
            all_activities.extend(activities)
        
        logger.info(f"Total activities found: {len(all_activities)}")
        
        # Calculate distances
        all_activities = self.calculate_distances(location, all_activities)
        
        # Remove duplicates
        seen_ids = set()
        unique_activities = []
        for activity in all_activities:
            if activity.place_id not in seen_ids:
                seen_ids.add(activity.place_id)
                unique_activities.append(activity)
        
        # Sort
        if sort_by == "rating":
            unique_activities.sort(
                key=lambda x: (x.rating or 0, x.user_ratings_total or 0),
                reverse=True
            )
        elif sort_by == "distance":
            unique_activities.sort(key=lambda x: x.distance or float('inf'))
        elif sort_by == "reviews":
            unique_activities.sort(key=lambda x: x.user_ratings_total or 0, reverse=True)
        
        logger.info(f"Returning {len(unique_activities)} unique activities")
        
        return TravelRecommendation(
            activities=unique_activities,
            total_count=len(unique_activities),
            search_location=location,
            timestamp=datetime.now().isoformat(),
            query_info={
                "query": location_query,
                "activity_types": activity_types,
                "radius": radius,
                "sort_by": sort_by
            }
        )
    

    # def generate_route_map_html(self, route: List[Activity], center: Dict[str, float]) -> str:
    #     """Generate HTML for route planning map"""
        
    #     markers_js = ""
    #     path_js = ""

    #     for idx, a in enumerate(route, 1):
    #         lat = a.location["lat"]
    #         lng = a.location["lng"]
    #         name = a.name.replace('"', "'")

    #         markers_js += f"""
    #         new google.maps.Marker({{
    #             position: {{ lat: {lat}, lng: {lng} }},
    #             map: map,
    #             label: "{idx}",
    #             title: "{name}"
    #         }});"""

    #         path_js += f"{{ lat: {lat}, lng: {lng} }},"

    #     html = f"""
    # <!DOCTYPE html>
    # <html>
    # <head>
    #     <meta charset="utf-8" />
    #     <title>Route Planning Map</title>

    #     <style>
    #         html, body, #map {{
    #             height: 100%;
    #             margin: 0;
    #             padding: 0;
    #         }}
    #     </style>

    #     <script>
    #     function initMap() {{
    #         const center = {{ lat: {center['lat']}, lng: {center['lng']} }};
    #         const map = new google.maps.Map(document.getElementById("map"), {{
    #             zoom: 13,
    #             center: center
    #         }});

    #         // Markers
    #         {markers_js}

    #         // Path polyline
    #         const routePath = [{path_js}];
    #         new google.maps.Polyline({{
    #             map: map,
    #             path: routePath,
    #             strokeColor: "#FF0000",
    #             strokeOpacity: 1.0,
    #             strokeWeight: 3
    #         }});
    #     }}
    #     </script>

    #     <script async defer
    #         src="https://maps.googleapis.com/maps/api/js?key={self.api_key}&callback=initMap">
    #     </script>
    # </head>

    # <body>
    #     <div id="map"></div>
    # </body>
    # </html>
    # """
    #     return html

    def generate_route_map_html(self, route: List[Activity], center: Dict[str, float]) -> str:
        """
        Generate an interactive Google Maps HTML page for a given route.

        Args:
            route: Ordered list of Activity objects representing the route.
            center: Map center as {"lat": float, "lng": float}.

        Returns:
            A complete HTML string that can be saved and opened in a browser.
        """
        markers_js = ""
        path_js = ""

        for idx, a in enumerate(route, 1):
            lat = a.location["lat"]
            lng = a.location["lng"]
            name = a.name.replace('"', "'")

            markers_js += f"""
            new google.maps.Marker({{
                position: {{ lat: {lat}, lng: {lng} }},
                map: map,
                label: "{idx}",
                title: "{name}"
            }});"""

            path_js += f"{{ lat: {lat}, lng: {lng} }},"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Route Planning Map</title>

    <style>
        html, body, #map {{
            height: 100%;
            margin: 0;
            padding: 0;
        }}
        .legend {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.9);
            padding: 8px 12px;
            border-radius: 4px;
            font-family: Arial, sans-serif;
            font-size: 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3);
        }}
    </style>

    <script>
    function initMap() {{
        const center = {{ lat: {center['lat']}, lng: {center['lng']} }};
        const map = new google.maps.Map(document.getElementById("map"), {{
            zoom: 13,
            center: center
        }});

        // Markers
        {markers_js}

        // Polyline connecting route points
        const routePath = [{path_js}];
        if (routePath.length > 1) {{
            new google.maps.Polyline({{
                map: map,
                path: routePath,
                strokeColor: "#FF0000",
                strokeOpacity: 1.0,
                strokeWeight: 3
            }});
        }}
    }}
    </script>

    <script async defer
        src="https://maps.googleapis.com/maps/api/js?key={self.api_key}&callback=initMap">
    </script>
</head>

<body>
    <div id="map"></div>
    <div class="legend">
        <strong>Route Map</strong><br/>
        Numbered markers indicate the visiting order.
    </div>
</body>
</html>
"""
        return html

    
    def plan_route(self, activities: List[Activity], start: Dict[str, float]) -> List[Activity]:
        """
        gready algorithm for route planning
        Args:
            activities: activity list
            start: starting location {"lat": ..., "lng": ...}
        
        Returns:
            sorted activity list as route
        """
        if not activities or not validate_location(start):
            return activities
        
        route = []
        current = start
        remaining = activities.copy()
        
        while remaining:
            # Find nearest activity
            nearest = min(
                remaining,
                key=lambda a: calculate_haversine_distance(current, a.location)
            )
            route.append(nearest)
            current = nearest.location
            remaining.remove(nearest)
        
        logger.info(f"Planned route with {len(route)} stops")
        return route
    
    def personalized_recommend(
        self,
        user_preferences: Dict[str, float],
        activities: List[Activity]
    ) -> List[Activity]:
        """
        based on user preferences for personalized sorting
        Args:
            user_preferences: {"museum": 0.8, "restaurant": 0.6, ...}
            activities: activity list
        
        Returns:
            sorted activity list
        """
        def score_activity(activity: Activity) -> float:
            score = 0.0
            for type_name in activity.types:
                if type_name in user_preferences:
                    score += user_preferences[type_name]
            
            # Add rating weight
            if activity.rating:
                score += activity.rating * 0.2
            
            return score
        
        sorted_activities = sorted(activities, key=score_activity, reverse=True)
        logger.info(f"Personalized sorting completed for {len(activities)} activities")
        return sorted_activities



    # def generate_map_url(self, activities: List[Activity], center: Dict[str, float]) -> str:
    #     """
    #     generate dynamic google map, return whole HTML content
    #     """
    #     # transform activities to JS objects
    #     activity_js = []
    #     for idx, a in enumerate(activities, 1):
    #         activity_js.append({
    #             "label": idx,
    #             "name": a.name.replace('"', "'"),
    #             "lat": a.location["lat"],
    #             "lng": a.location["lng"]
    #         })

    #     # convert to JSON string
    #     activities_json = json.dumps(activity_js)

    #     # dynamic HTML
    #     html = f"""
    # <!DOCTYPE html>
    # <html>
    # <head>
    # <meta charset="utf-8">
    # <title>Travel Activities Map</title>

    # <style>
    # html, body, #map {{
    #     height: 100%;
    #     margin: 0;
    #     padding: 0;
    # }}
    # </style>

    # <script>
    # function initMap() {{
    #     const center = {{ lat: {center['lat']}, lng: {center['lng']} }};

    #     const map = new google.maps.Map(document.getElementById("map"), {{
    #         zoom: 13,
    #         center: center
    #     }});

    #     const activities = {activities_json};
    #     const path = [];

    #     // Add markers
    #     activities.forEach(a => {{
    #         const pos = {{ lat: a.lat, lng: a.lng }};
    #         path.push(pos);

    #         new google.maps.Marker({{
    #             position: pos,
    #             map: map,
    #             label: String(a.label),
    #             title: a.name
    #         }});
    #     }});

    #     // Add polyline to connect points
    #     if (path.length > 1) {{
    #         new google.maps.Polyline({{
    #             map: map,
    #             path: path,
    #             strokeColor: "#FF0000",
    #             strokeOpacity: 1.0,
    #             strokeWeight: 3
    #         }});
    #     }}
    # }}
    # </script>

    # <script async defer
    # src="https://maps.googleapis.com/maps/api/js?key={self.api_key}&callback=initMap">
    # </script>

    # </head>
    # <body>
    # <div id="map"></div>
    # </body>
    # </html>
    # """

    #     return html

    def generate_map_url(self, activities: List[Activity], center: Dict[str, float]) -> str:
        """
        Generate an interactive Google Maps HTML page for a list of activities.

        This uses the Google Maps JavaScript API (not Static Maps) and returns
        a full HTML document as a string. Save it to a file (e.g., dynamic_map.html)
        and open it in a browser.

        Args:
            activities: List of Activity objects to display on the map.
            center: Map center as {"lat": float, "lng": float}.

        Returns:
            A complete HTML string.
        """
        activity_js = []
        for idx, a in enumerate(activities, 1):
            activity_js.append({
                "label": idx,
                "name": a.name.replace('"', "'"),
                "lat": a.location["lat"],
                "lng": a.location["lng"]
            })

        activities_json = json.dumps(activity_js)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Travel Activities Map</title>

    <style>
    html, body, #map {{
        height: 100%;
        margin: 0;
        padding: 0;
    }}
    .legend {{
        position: absolute;
        top: 10px;
        left: 10px;
        background: rgba(255, 255, 255, 0.9);
        padding: 8px 12px;
        border-radius: 4px;
        font-family: Arial, sans-serif;
        font-size: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    }}
    </style>

    <script>
    function initMap() {{
        const center = {{ lat: {center['lat']}, lng: {center['lng']} }};

        const map = new google.maps.Map(document.getElementById("map"), {{
            zoom: 13,
            center: center
        }});

        const activities = {activities_json};
        const path = [];

        // Add markers
        activities.forEach(a => {{
            const pos = {{ lat: a.lat, lng: a.lng }};
            path.push(pos);

            new google.maps.Marker({{
                position: pos,
                map: map,
                label: String(a.label),
                title: a.name
            }});
        }});

        // Draw a polyline connecting all activities in order
        if (path.length > 1) {{
            new google.maps.Polyline({{
                map: map,
                path: path,
                strokeColor: "#FF0000",
                strokeOpacity: 1.0,
                strokeWeight: 3
            }});
        }}
    }}
    </script>

    <script async defer
        src="https://maps.googleapis.com/maps/api/js?key={self.api_key}&callback=initMap">
    </script>
</head>
<body>
    <div id="map"></div>
    <div class="legend">
        <strong>Activity Map</strong><br/>
        Numbered markers indicate the activity list order.
    </div>
</body>
</html>
"""
        return html



