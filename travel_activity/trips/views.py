from django.shortcuts import render

# Create your views here.
from .models import Trip

def home(request):
    return render(request, 'home.html')