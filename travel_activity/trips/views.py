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

# Standard Library Imports
import os
import sys

# Local Imports
from .models import Activity, Review, Recommendation, SavedActivity, User, Trip
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
                max_per_type=5,
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
    Display the saved activities for the logged-in user.
    """
    saved_activities = SavedActivity.objects.filter(user=request.user).select_related('activity').order_by('-saved_at')

    return render(request, 'saved.html', {
        'saved_activities': saved_activities,
        'user': request.user
    })
