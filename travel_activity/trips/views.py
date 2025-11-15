from django.shortcuts import render

# Create your views here.
from .models import Trip

def home(request):
    trips = Trip.objects.all()
    return render(request, 'index.html', {'trips': trips})