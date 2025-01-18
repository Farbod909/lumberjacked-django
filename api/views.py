from rest_framework import generics

from .models import Movement, MovementLog, Workout
from .serializers import MovementSerializer, MovementLogSerializer, WorkoutSerializer


class MovementList(generics.ListCreateAPIView):
    queryset = Movement.objects.all()
    serializer_class = MovementSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class MovementDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Movement.objects.all()
    serializer_class = MovementSerializer

class MovementLogList(generics.ListCreateAPIView):
    queryset = MovementLog.objects.all()
    serializer_class = MovementLogSerializer

class MovementLogDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = MovementLog.objects.all()
    serializer_class = MovementLogSerializer

class WorkoutList(generics.ListCreateAPIView):
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class WorkoutDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer
