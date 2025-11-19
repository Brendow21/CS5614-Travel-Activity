from django.contrib import admin
from .models import User, Trip, Activity, Review, Recommendation, SavedActivity

admin.site.register(User)
admin.site.register(Trip)
admin.site.register(Activity)
admin.site.register(Review)
admin.site.register(Recommendation)
admin.site.register(SavedActivity)