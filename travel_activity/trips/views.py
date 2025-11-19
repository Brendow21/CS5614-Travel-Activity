from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from .models import Activity, Review, Recommendation, SavedActivity, User, Trip
from .serializers import ActivitySerializer, RecommendationSerializer, SavedActivitySerializer
from .recommendations import RecommendationEngine


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