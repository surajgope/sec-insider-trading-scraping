
from django.urls import path
from  .views import *
urlpatterns = [
    path('', display_data, name='insider-trading'),
]