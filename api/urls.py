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
    path('workouts/<int:id>/end/', views.WorkoutEnd.as_view(), name='workout-end'),
    path('workouts/current/', views.WorkoutCurrent.as_view(), name='workout-current'),
    path('workout-movements/', views.WorkoutMovementList.as_view(), name='workout-movement-list'),
    path('workout-movements/<int:id>/', views.WorkoutMovementDetail.as_view(), name='workout-movement-detail'),
    path('workout-templates/', views.WorkoutTemplateList.as_view(), name='workout-template-list'),
    path('workout-templates/<int:id>/', views.WorkoutTemplateDetail.as_view(), name='workout-template-detail'),
    path('movement-log-templates/', views.MovementLogTemplateList.as_view(), name='movement-log-template-list'),
    path('movement-log-templates/<int:id>/', views.MovementLogTemplateDetail.as_view(), name='movement-log-template-detail'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
