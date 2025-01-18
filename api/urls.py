from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views


urlpatterns = [
    path('movements/', views.MovementList.as_view()),
    path('movements/<int:pk>/', views.MovementDetail.as_view()),
    path('movement-logs/', views.MovementLogList.as_view()),
    path('movement-logs/<int:pk>/', views.MovementLogDetail.as_view()),
    path('workouts/', views.WorkoutList.as_view()),
    path('workouts/<int:pk>/', views.WorkoutDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
