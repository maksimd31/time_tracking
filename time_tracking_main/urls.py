from django.urls import path

from . import views
# from crm_car_wash.new_time_register import views

urlpatterns = [
    path('', views.index, name='home'),


]
