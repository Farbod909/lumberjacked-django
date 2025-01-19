from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views


urlpatterns = [
    path('movements/', views.MovementList.as_view(), name='movement-list'),
    path('movements/<int:id>/', views.MovementDetail.as_view(), name='movement-detail'),
    path('movement-logs/', views.MovementLogList.as_view(), name='movement-log-list'),
    path('movement-logs/<int:id>/', views.MovementLogDetail.as_view(), name='movement-log-detail'),
    path('workouts/', views.WorkoutList.as_view(), name='workout-list'),
    path('workouts/<int:id>/', views.WorkoutDetail.as_view(), name='workout-detail'),
    path('workouts/<int:id>/end', views.WorkoutEnd.as_view(), name='workout-end'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
