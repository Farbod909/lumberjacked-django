from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Movement, MovementLog, Workout
from .permissions import IsMovementOwner, IsMovementLogOwner, IsWorkoutOwner
from .serializers import MovementSerializer, MovementLogSerializer, WorkoutSerializer

class MovementList(generics.ListCreateAPIView):
    serializer_class = MovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Movement.objects.filter(author=user).order_by('name')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class MovementDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Movement.objects.all()
    lookup_field = 'id'
    serializer_class = MovementSerializer
    permission_classes = [IsAuthenticated, IsMovementOwner]

class MovementLogList(generics.ListCreateAPIView):
    serializer_class = MovementLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return MovementLog.objects.filter(workout__user=user)

class MovementLogDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = MovementLog.objects.all()
    lookup_field = 'id'
    serializer_class = MovementLogSerializer
    permission_classes = [IsAuthenticated, IsMovementLogOwner]

class WorkoutList(generics.ListCreateAPIView):
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Workout.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class WorkoutDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Workout.objects.all()
    lookup_field = 'id'
    serializer_class = WorkoutSerializer
    permission_classes = [IsAuthenticated, IsWorkoutOwner]
