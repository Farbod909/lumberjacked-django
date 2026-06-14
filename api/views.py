from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Movement, MovementLog, MovementLogTemplate, Workout, WorkoutMovement, WorkoutTemplate
from .permissions import (
    IsMovementOwner, IsMovementLogOwner, IsMovementLogTemplateOwner,
    IsWorkoutOwner, IsWorkoutMovementOwner, IsWorkoutTemplateOwner,
)
from .serializers import (
    MovementSerializer, MovementLogSerializer,
    MovementLogTemplateSerializer,
    WorkoutSerializer, WorkoutMovementSerializer,
    WorkoutTemplateSerializer,
    WorkoutWithLatestLogsSerializer, WorkoutWithRecordedLogsSerializer,
)

_WORKOUT_MOVEMENTS_PREFETCH = Prefetch(
    'workout_movements',
    queryset=WorkoutMovement.objects.select_related('movement', 'template', 'movement_log').order_by('order'),
)


class MovementList(generics.ListCreateAPIView):
    serializer_class = MovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Movement.objects.filter(author=self.request.user).order_by('name')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MovementDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Movement.objects.all()
    lookup_field = 'id'
    serializer_class = MovementSerializer
    permission_classes = [IsAuthenticated, IsMovementOwner]


class WorkoutMovementList(generics.ListCreateAPIView):
    serializer_class = WorkoutMovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = WorkoutMovement.objects.filter(workout__user=self.request.user).select_related('movement', 'template')
        if 'workout' in self.request.query_params:
            qs = qs.filter(workout=self.request.query_params['workout'])
        return qs.order_by('workout', 'order')

    def perform_create(self, serializer):
        workout = serializer.validated_data['workout']
        if workout.user != self.request.user:
            raise PermissionDenied("Workout is not owned by the authenticated user.")
        movement = serializer.validated_data['movement']
        if movement.author != self.request.user:
            raise PermissionDenied("Movement is not owned by the authenticated user.")
        template = serializer.validated_data.get('template')
        if template and template.author != self.request.user:
            raise PermissionDenied("Template is not owned by the authenticated user.")
        next_order = workout.workout_movements.count()
        serializer.save(order=next_order)


class WorkoutMovementDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorkoutMovement.objects.select_related('movement', 'template')
    lookup_field = 'id'
    serializer_class = WorkoutMovementSerializer
    permission_classes = [IsAuthenticated, IsWorkoutMovementOwner]

    def perform_destroy(self, instance):
        try:
            instance.movement_log
            raise ValidationError("Cannot remove a movement that has an associated log.")
        except MovementLog.DoesNotExist:
            instance.delete()


class MovementLogList(generics.ListCreateAPIView):
    serializer_class = MovementLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MovementLog.objects.filter(workout_movement__workout__user=self.request.user)
        if 'workout_movement' in self.request.query_params:
            qs = qs.filter(workout_movement=self.request.query_params['workout_movement'])
        if 'movement' in self.request.query_params:
            qs = qs.filter(workout_movement__movement=self.request.query_params['movement'])
        if 'workout' in self.request.query_params:
            qs = qs.filter(workout_movement__workout=self.request.query_params['workout'])
        return qs.order_by('-timestamp')

    def perform_create(self, serializer):
        return serializer.save(timestamp=timezone.now())


class MovementLogDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = MovementLog.objects.all()
    lookup_field = 'id'
    serializer_class = MovementLogSerializer
    permission_classes = [IsAuthenticated, IsMovementLogOwner]


class WorkoutList(generics.ListCreateAPIView):
    serializer_class = WorkoutWithRecordedLogsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Workout.objects
            .filter(user=self.request.user)
            .order_by('-start_timestamp')
            .prefetch_related(_WORKOUT_MOVEMENTS_PREFETCH)
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WorkoutDetail(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'id'
    serializer_class = WorkoutWithRecordedLogsSerializer
    permission_classes = [IsAuthenticated, IsWorkoutOwner]

    def get_queryset(self):
        return Workout.objects.prefetch_related(_WORKOUT_MOVEMENTS_PREFETCH)


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
        workout.end_timestamp = timezone.now()
        workout.save()
        serializer = WorkoutSerializer(workout)
        return Response(serializer.data)


class WorkoutCurrent(APIView):
    permission_classes = [IsAuthenticated, IsWorkoutOwner]

    def get(self, request, format=None):
        workout = (
            Workout.objects
            .filter(user=request.user, end_timestamp__isnull=True)
            .order_by("-start_timestamp")
            .first()
        )
        if workout is None:
            raise Http404("Current workout does not exist.")

        workout_serializer = WorkoutWithLatestLogsSerializer(workout)
        return Response(workout_serializer.data)


class WorkoutTemplateList(generics.ListCreateAPIView):
    serializer_class = WorkoutTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkoutTemplate.objects.filter(author=self.request.user).order_by('name')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class WorkoutTemplateDetail(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'id'
    serializer_class = WorkoutTemplateSerializer
    permission_classes = [IsAuthenticated, IsWorkoutTemplateOwner]

    def get_queryset(self):
        return WorkoutTemplate.objects.all()


class MovementLogTemplateList(generics.ListCreateAPIView):
    serializer_class = MovementLogTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MovementLogTemplate.objects.filter(author=self.request.user)
        if 'movement' in self.request.query_params:
            qs = qs.filter(movement=self.request.query_params['movement'])
        return qs.order_by('name')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MovementLogTemplateDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = MovementLogTemplate.objects.all()
    lookup_field = 'id'
    serializer_class = MovementLogTemplateSerializer
    permission_classes = [IsAuthenticated, IsMovementLogTemplateOwner]
