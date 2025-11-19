from rest_framework import serializers
from .models import Activity, Review, Recommendation, SavedActivity

class ActivitySerializer(serializers.ModelSerializer):
    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Activity
        fields = '__all__'
    
    def get_review_count(self, obj):
        return obj.reviews.count()
    
    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews:
            return round(sum(float(r.rating) for r in reviews) / len(reviews), 1)
        return None


class RecommendationSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer(read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = Recommendation
        fields = '__all__'


class SavedActivitySerializer(serializers.ModelSerializer):
    activity = ActivitySerializer(read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = SavedActivity
        fields = '__all__'