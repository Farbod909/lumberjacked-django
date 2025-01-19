from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from datetime import datetime
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
    serializer_class = WorkoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Workout.objects.filter(user=user).order_by('-start_timestamp')
    
    def perform_create(self, serializer):
        if 'movements' in serializer.validated_data:
            initial_movements = serializer.validated_data['movements']
        else:
            initial_movements = []

        if 'template' in self.request.query_params.keys():
            try:
                workout = \
                    Workout.objects.get(id=self.request.query_params['template'])
            except Workout.DoesNotExist:
                raise HttpResponseBadRequest
            initial_movements = workout.movements
        serializer.save(user=self.request.user, movements=initial_movements)

class WorkoutDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Workout.objects.all()
    lookup_field = 'id'
    serializer_class = WorkoutSerializer
    permission_classes = [IsAuthenticated, IsWorkoutOwner]

class WorkoutEnd(APIView):
    queryset = Workout.objects.all()
    lookup_field = 'id'
    serializer_class = WorkoutSerializer
    permission_classes = [IsAuthenticated, IsWorkoutOwner]

    def get_object(self, id):
        workout = get_object_or_404(self.queryset, id=self.kwargs["id"])
        self.check_object_permissions(self.request, workout)
        return workout

    def get(self, request, id, format=None):
        workout = self.get_object(id)
        workout.end_timestamp = datetime.now()
        workout.save()
        serializer = WorkoutSerializer(workout)
        return Response(serializer.data)
