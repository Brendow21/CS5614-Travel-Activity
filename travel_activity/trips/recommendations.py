from django.db.models import Q, Avg
from .models import Activity, Review, User, Trip, TripActivity
from math import radians, sin, cos, sqrt, atan2

class RecommendationEngine:
    """Generate personalized activity recommendations"""
    
    @staticmethod
    def filter_activities(preferences):
        """
        Filter activities based on user preferences
        """
        activities = Activity.objects.all()
        
        if preferences.get('min_price'):
            activities = activities.filter(cost__gte=preferences['min_price'])
        
        if preferences.get('max_price'):
            activities = activities.filter(cost__lte=preferences['max_price'])
        
        if preferences.get('category'):
            activities = activities.filter(category__icontains=preferences['category'])
        
        if preferences.get('duration'):
            duration_map = {
                'quick': (0, 120),
                'half-day': (120, 240),
                'full-day': (240, 480),
                'multi-day': (480, 100000)
            }
            if preferences['duration'] in duration_map:
                min_dur, max_dur = duration_map[preferences['duration']]
                activities = activities.filter(
                    duration__gte=min_dur,
                    duration__lte=max_dur
                )
        
        if preferences.get('min_rating'):
            activities = activities.filter(rating__gte=preferences['min_rating'])
        
        if preferences.get('location'):
            activities = activities.filter(location__icontains=preferences['location'])
        
        return activities.order_by('-rating', 'cost')
    
    @staticmethod
    def generate_recommendations(user, limit=10):
        """Generate personalized recommendations for a user"""
        user_liked_categories = Review.objects.filter(
            user=user,
            rating__gte=4.0
        ).values_list('activity__category', flat=True).distinct()
        
        recommendations = Activity.objects.filter(
            category__in=user_liked_categories
        ).exclude(
            reviews__user=user
        ).order_by('-rating')[:limit]
        
        return recommendations
    
    @staticmethod
    def calculate_recommendation_score(user, activity):
        """Calculate a recommendation score (0-100)"""
        score = 50.0
        
        user_reviews = Review.objects.filter(user=user, rating__gte=4.0)
        liked_categories = [r.activity.category for r in user_reviews]
        
        if activity.category in liked_categories:
            score += 20
        
        if activity.rating:
            score += float(activity.rating) * 5
        
        review_count = activity.reviews.count()
        if review_count > 10:
            score += 10
        elif review_count > 5:
            score += 5
        
        return min(score, 100)

    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        R = 6371

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    @staticmethod
    def generate_trip_recommendations(trip, user, limit=10):
        """
        Generate recommendations for activities to add to a specific trip.

        Scoring based on:
        - User preferences (40%)
        - Location proximity (30%)
        - Activity rating (20%)
        - Category diversity (10%)
        """
        existing_activities = TripActivity.objects.filter(trip=trip).values_list('activity_id', flat=True)
        existing_categories = TripActivity.objects.filter(trip=trip).values_list('activity__category', flat=True)

        avg_lat = TripActivity.objects.filter(trip=trip).aggregate(Avg('activity__latitude'))['activity__latitude__avg']
        avg_lng = TripActivity.objects.filter(trip=trip).aggregate(Avg('activity__longitude'))['activity__longitude__avg']

        if not avg_lat or not avg_lng:
            avg_lat, avg_lng = 0, 0

        all_activities = Activity.objects.exclude(activity_id__in=existing_activities).exclude(latitude__isnull=True).exclude(longitude__isnull=True)

        scored_activities = []
        user_prefs = user.preferences if isinstance(user.preferences, list) else []

        for activity in all_activities:
            score = 0.0

            pref_score = 40 if any(pref.lower() in activity.category.lower() for pref in user_prefs) else 0

            distance = RecommendationEngine.haversine_distance(
                float(avg_lat), float(avg_lng),
                float(activity.latitude), float(activity.longitude)
            )
            if distance < 5:
                proximity_score = 30
            elif distance < 15:
                proximity_score = 20
            elif distance < 30:
                proximity_score = 10
            else:
                proximity_score = 0

            rating_score = (float(activity.rating or 0) / 5.0) * 20

            diversity_score = 10 if activity.category not in existing_categories else 0

            total_score = pref_score + proximity_score + rating_score + diversity_score

            scored_activities.append({
                'activity': activity,
                'score': total_score,
                'distance_km': round(distance, 1)
            })

        scored_activities.sort(key=lambda x: x['score'], reverse=True)

        return scored_activities[:limit]