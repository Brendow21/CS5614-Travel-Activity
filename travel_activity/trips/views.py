# Django Imports
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import logout
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings

# Rest Framework Imports
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt

# Standard Library Imports
import os
import sys

# Local Imports
from .models import Activity, Review, Recommendation, SavedActivity, User, Trip, TripActivity
from .serializers import ActivitySerializer, RecommendationSerializer, SavedActivitySerializer
from .recommendations import RecommendationEngine
from .forms import CustomUserCreationForm

# Retrieve the RealTimeTravelActivitySystem from the src directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, '..'))
from src.travel_system import RealTimeTravelActivitySystem

# Initialize the system with your Google API key
API_KEY = settings.GOOGLE_MAPS_API_KEY
travel_system = RealTimeTravelActivitySystem(api_key=API_KEY)

def home(request):
    return render(request, 'home.html')

class ActivityViewSet(viewsets.ModelViewSet):
    """API endpoints for activities"""
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    
    @action(detail=False, methods=['get'])
    def filter(self, request):
        """Filter activities based on preferences"""
        preferences = {}
        
        if request.query_params.get('min_price'):
            preferences['min_price'] = float(request.query_params.get('min_price'))
        
        if request.query_params.get('max_price'):
            preferences['max_price'] = float(request.query_params.get('max_price'))
        
        if request.query_params.get('category'):
            preferences['category'] = request.query_params.get('category')
        
        if request.query_params.get('duration'):
            preferences['duration'] = request.query_params.get('duration')
        
        if request.query_params.get('min_rating'):
            preferences['min_rating'] = float(request.query_params.get('min_rating'))
        
        if request.query_params.get('location'):
            preferences['location'] = request.query_params.get('location')
        
        activities = RecommendationEngine.filter_activities(preferences)
        serializer = self.get_serializer(activities, many=True)
        
        return Response({
            'count': activities.count(),
            'filters_applied': preferences,
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        """Save an activity for later"""
        activity = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        saved, created = SavedActivity.objects.get_or_create(
            user=user,
            activity=activity
        )
        
        if created:
            return Response(
                {'status': 'saved', 'activity': activity.title},
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {'status': 'already_saved', 'activity': activity.title},
                status=status.HTTP_200_OK
            )


@api_view(['POST'])
def generate_recommendations(request):
    """Generate personalized recommendations"""
    user_id = request.data.get('user_id')
    limit = request.data.get('limit', 10)
    
    if not user_id:
        return Response(
            {'error': 'user_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    recommendations = RecommendationEngine.generate_recommendations(user, limit=limit)
    
    results = []
    for activity in recommendations:
        score = RecommendationEngine.calculate_recommendation_score(user, activity)
        results.append({
            'activity': ActivitySerializer(activity).data,
            'score': score,
            'reason': f"Based on your interest in {activity.category}"
        })
    
    return Response({
        'user': user.name,
        'recommendation_count': len(results),
        'recommendations': results
    })


@api_view(['GET'])
def user_saved_activities(request, user_id):
    """Get all saved activities for a user"""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    saved = SavedActivity.objects.filter(user=user)
    serializer = SavedActivitySerializer(saved, many=True)
    
    return Response({
        'user': user.name,
        'saved_count': saved.count(),
        'saved_activities': serializer.data
    })

@api_view(['POST', 'OPTIONS'])
def save_activity_from_search(request):
    """Save an activity from search results (Google Places data)"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return Response(status=status.HTTP_200_OK)

    # Check if user is authenticated
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        # Get activity data from request
        data = request.data
        place_id = data.get('place_id')
        name = data.get('name')
        address = data.get('address')
        lat = data.get('lat')
        lng = data.get('lng')
        rating = data.get('rating')
        price_level = data.get('price_level')
        types = data.get('types', [])
        photo_url = data.get('photo_url')

        # Validate required fields
        if not place_id or not name:
            return Response(
                {'error': 'place_id and name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if activity already exists in database
        activity, created = Activity.objects.get_or_create(
            place_id=place_id,
            defaults={
                'title': name,
                'location': address or '',
                'description': '',
                'category': types[0] if types else 'tourist_attraction',
                'cost': price_level or 0,
                'rating': rating or 0,
                'photo_url': photo_url or '',
                'latitude': lat,
                'longitude': lng
            }
        )

        # Save to user's saved activities
        saved, saved_created = SavedActivity.objects.get_or_create(
            user=request.user,
            activity=activity
        )

        if saved_created:
            return Response(
                {
                    'status': 'saved',
                    'activity': activity.title,
                    'message': 'Activity saved successfully!'
                },
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {
                    'status': 'already_saved',
                    'activity': activity.title,
                    'message': 'Activity is already in your saved list'
                },
                status=status.HTTP_200_OK
            )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def search_view(request):
    query = request.GET.get("q")

    results = []
    error_message = None

    if query:
        try:
            recommendation = travel_system.recommend_activities(
                location_query=query,
                activity_types=[
                    "tourist_attraction", "restaurant", "museum",
                    "park", "shopping_mall", "night_club", "art_gallery",
                    "cafe", "bar", "movie_theater"
                ],
                radius=5000,
                max_per_type=20,
                sort_by="rating"
            )

            results = recommendation.activities

        except Exception as e:
            error_message = str(e)

    return render(request, "search.html", {
        "query": query,
        "results": results,
        "error_message": error_message,
        "google_api_key": API_KEY
    })

# User Account Views

@login_required
def profile_view(request):
    """
    Display the profile page for the logged-in user."""
    from datetime import date

    # Handle profile updates
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.bio = request.POST.get('bio', '')
        user.phone = request.POST.get('phone', '')

        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']

        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')

    # Get user trips
    all_trips = Trip.objects.filter(user=request.user).order_by('start_date')
    today = date.today()

    upcoming_trips = all_trips.filter(start_date__gte=today)[:3]
    past_trips = all_trips.filter(end_date__lt=today).order_by('-end_date')[:3]

    # Preference options
    prefs_list = ['Adventure', 'Beach', 'City', 'Culture', 'Food', 'History', 'Nature', 'Shopping', 'Sports']

    return render(request, 'account/profile.html', {
        'user': request.user,
        'upcoming_trips_list': upcoming_trips,
        'past_trips_list': past_trips,
        'prefs_list': prefs_list,
    })

def register_view(request):
    """
    Handle user registration."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'account/register.html', {'form': form})

@require_POST
def logout_view(request):
    """
    Logs out the user via POST request and redirects to home.
    """
    logout(request)
    return redirect('home')

@login_required(login_url='login')
def saved_view(request):
    """
    Display the saved trips and their activities for the logged-in user.
    """
    # Get all user trips with their activities
    trips = Trip.objects.filter(user=request.user).order_by('-start_date')

    # Build trip data with activities
    trips_with_activities = []
    for trip in trips:
        trip_activities = TripActivity.objects.filter(trip=trip).select_related('activity').order_by('order', 'added_at')
        trips_with_activities.append({
            'trip': trip,
            'activities': trip_activities,
            'activity_count': trip_activities.count()
        })

    return render(request, 'saved.html', {
        'trips_with_activities': trips_with_activities,
        'user': request.user
    })


# Trip Management API Endpoints

@api_view(['GET'])
def user_trips(request):
    """Get all trips for the logged-in user"""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    trips = Trip.objects.filter(user=request.user).order_by('-start_date')

    trips_data = []
    for trip in trips:
        activity_count = TripActivity.objects.filter(trip=trip).count()
        trips_data.append({
            'id': trip.id,
            'destination': trip.destination,
            'start_date': trip.start_date.strftime('%Y-%m-%d'),
            'end_date': trip.end_date.strftime('%Y-%m-%d'),
            'activity_count': activity_count
        })

    return Response({'trips': trips_data})


@api_view(['POST'])
def create_trip(request):
    """Create a new trip"""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        destination = request.data.get('destination')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if not destination or not start_date or not end_date:
            return Response(
                {'error': 'destination, start_date, and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        trip = Trip.objects.create(
            user=request.user,
            destination=destination,
            start_date=start_date,
            end_date=end_date
        )

        return Response({
            'status': 'success',
            'trip_id': trip.id,
            'message': 'Trip created successfully'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def add_activity_to_trip(request):
    """Add an activity to a trip"""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        trip_id = request.data.get('trip_id')
        activity_data = request.data.get('activity_data')

        if not trip_id or not activity_data:
            return Response(
                {'error': 'trip_id and activity_data are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the trip
        try:
            trip = Trip.objects.get(id=trip_id, user=request.user)
        except Trip.DoesNotExist:
            return Response(
                {'error': 'Trip not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create or get the activity
        place_id = activity_data.get('place_id')
        name = activity_data.get('name')
        address = activity_data.get('address')
        lat = activity_data.get('lat')
        lng = activity_data.get('lng')
        rating = activity_data.get('rating')
        price_level = activity_data.get('price_level')
        types = activity_data.get('types', [])
        photo_url = activity_data.get('photo_url')

        activity, created = Activity.objects.get_or_create(
            place_id=place_id,
            defaults={
                'title': name,
                'location': address or '',
                'description': '',
                'category': types[0] if types else 'tourist_attraction',
                'cost': price_level or 0,
                'rating': rating or 0,
                'photo_url': photo_url or '',
                'latitude': lat,
                'longitude': lng
            }
        )

        # Add activity to trip
        trip_activity, ta_created = TripActivity.objects.get_or_create(
            trip=trip,
            activity=activity
        )

        if ta_created:
            return Response({
                'status': 'success',
                'trip_name': trip.destination,
                'message': f'Activity added to {trip.destination}'
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'status': 'already_added',
                'trip_name': trip.destination,
                'message': 'Activity already in this trip'
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@login_required
def trip_map_view(request, trip_id):
    """
    Display the map view for a specific trip showing all its activities.
    """
    try:
        trip = Trip.objects.get(id=trip_id, user=request.user)
        trip_activities = TripActivity.objects.filter(trip=trip).select_related('activity').order_by('order', 'added_at')

        return render(request, 'trip_map.html', {
            'trip': trip,
            'trip_activities': trip_activities,
            'google_api_key': settings.GOOGLE_MAPS_API_KEY
        })
    except Trip.DoesNotExist:
        messages.error(request, 'Trip not found.')
        return redirect('saved')


@api_view(['DELETE'])
def remove_activity_from_trip(request, trip_id, activity_id):
    """Remove an activity from a trip"""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        # Get the trip
        try:
            trip = Trip.objects.get(id=trip_id, user=request.user)
        except Trip.DoesNotExist:
            return Response(
                {'error': 'Trip not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get the trip activity
        try:
            trip_activity = TripActivity.objects.get(trip=trip, activity__activity_id=activity_id)
        except TripActivity.DoesNotExist:
            return Response(
                {'error': 'Activity not found in this trip'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete the trip activity
        trip_activity.delete()

        return Response({
            'status': 'success',
            'message': 'Activity removed from trip'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
