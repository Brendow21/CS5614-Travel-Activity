"""
URL configuration for travel_activity project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
# Import the views module from the trips app
from trips import views
from trips.views import (
    ActivityViewSet, generate_recommendations, user_saved_activities,
    save_activity_from_search, user_trips, create_trip, add_activity_to_trip,
    remove_activity_from_trip
)

router = DefaultRouter()
router.register(r'activities', ActivityViewSet, basename='activity')

urlpatterns = [
    path('admin/', admin.site.urls),
    # General routes
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),
    path('search/', views.search_view, name='search'),
    path('search/', views.search_view, name='search_view'),
    path('profile/', views.profile_view, name='profile'),
    path('saved/', views.saved_view, name='saved'),

    # Auth routes
    path('login/', auth_views.LoginView.as_view(template_name='account/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='account/logout.html'), name='logout'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # API routes
    path('api/', include(router.urls)),
    path('api/recommendations/generate/', generate_recommendations, name='generate-recommendations'),
    path('api/users/<int:user_id>/saved/', user_saved_activities, name='user-saved-activities'),
    path('api/activities/save-from-search/', save_activity_from_search, name='save-activity-from-search'),

    # Trip API routes
    path('api/trips/user-trips/', user_trips, name='user-trips'),
    path('api/trips/create/', create_trip, name='create-trip'),
    path('api/trips/add-activity/', add_activity_to_trip, name='add-activity-to-trip'),
    path('api/trips/<int:trip_id>/remove-activity/<int:activity_id>/', remove_activity_from_trip, name='remove-activity-from-trip'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)