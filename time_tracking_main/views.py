from django.shortcuts import render
from .models import TimeInterval

def index(request):

    time = TimeInterval.objects.all()
    return render(request, 'time_tracking_main/index.html', {'time': time})
