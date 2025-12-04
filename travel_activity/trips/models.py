from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Extend Django's AbstractUser to add extra fields if needed.
    username, email, password are already included in AbstractUser.
    """
    bio = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)


class Trip(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    destination = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.destination} ({self.user.name})"


class Activity(models.Model):
    """Travel activities - restaurants, museums, tours, etc."""
    activity_id = models.AutoField(primary_key=True)
    place_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text="Google Places ID")
    title = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in minutes", null=True, blank=True)
    location = models.CharField(max_length=200)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    photo_url = models.URLField(max_length=500, null=True, blank=True)
    accessibility = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'activities'
        verbose_name_plural = 'Activities'
    
    def __str__(self):
        return self.title


class Review(models.Model):
    """User reviews for activities"""
    review_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='reviews')
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reviews'
    
    def __str__(self):
        return f"Review by {self.user.name} for {self.activity.title}"


class Recommendation(models.Model):
    """Personalized activity recommendations"""
    rec_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    score = models.FloatField()
    reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'recommendations'
        ordering = ['-score']
    
    def __str__(self):
        return f"Rec for {self.user.name}: {self.activity.title} (score: {self.score})"


class SavedActivity(models.Model):
    """Activities saved by users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_activities')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saved_activities'
        unique_together = ('user', 'activity')
        verbose_name_plural = 'Saved Activities'

    def __str__(self):
        return f"{self.user.name} saved {self.activity.title}"


class TripActivity(models.Model):
    """Activities associated with trips"""
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='trip_activities')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='trip_activities')
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True, help_text="Personal notes about this activity for the trip")
    order = models.IntegerField(default=0, help_text="Order in itinerary")

    class Meta:
        db_table = 'trip_activities'
        unique_together = ('trip', 'activity')
        ordering = ['order', 'added_at']
        verbose_name_plural = 'Trip Activities'

    def __str__(self):
        return f"{self.activity.title} in {self.trip.destination}"
    