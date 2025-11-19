from django.db import models

class User(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name

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
    title = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in minutes")
    location = models.CharField(max_length=200)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
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