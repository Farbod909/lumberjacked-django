from django.db.models import (
    BooleanField, Case, JSONField, OuterRef,
    Subquery, Value, When, IntegerField
)
from django.db.models.functions import JSONObject
from django.http import Http404
from django.shortcuts import get_object_or_404
from datetime import datetime
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Movement, MovementLog, Workout
from .permissions import IsMovementOwner, IsMovementLogOwner, IsWorkoutOwner
from .serializers import (
    MovementSerializer, MovementLogSerializer, 
    WorkoutSerializer, WorkoutWithLatestLogsSerializer,
    WorkoutWithRecordedLogsSerializer
)

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

    def _check_create_permissions(self, validated_data):
        movement = validated_data['movement']
        workout = validated_data['workout']
        if movement.author != self.request.user or workout.user != self.request.user:
                raise PermissionDenied("Movement or workout is not owned by the authenticated user.")

    def get_queryset(self):
        user = self.request.user
        qs = MovementLog.objects.filter(workout__user=user)
        if 'movement' in self.request.query_params.keys():
            qs = qs.filter(movement=self.request.query_params['movement'])

        if 'workout' in self.request.query_params.keys():
            qs = qs.filter(workout=self.request.query_params['workout'])
        
        return qs.order_by('-timestamp')
            
    def perform_create(self, serializer):
        self._check_create_permissions(serializer.validated_data)
        return serializer.save(timestamp=timezone.now())


class MovementLogDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = MovementLog.objects.all()
    lookup_field = 'id'
    serializer_class = MovementLogSerializer
    permission_classes = [IsAuthenticated, IsMovementLogOwner]

    def _check_update_permissions(self, validated_data):
        if 'movement' in validated_data.keys():
            movement = validated_data['movement']
            if movement.author != self.request.user:
                raise PermissionDenied("Movement is not owned by the authenticated user.")
            
        if 'workout' in validated_data.keys():
            workout = validated_data['workout']
            if workout.user != self.request.user:
                raise PermissionDenied("Workout is not owned by the authenticated user.")

    def perform_update(self, serializer):
        self._check_update_permissions(serializer.validated_data)
        return serializer.save()

class WorkoutList(generics.ListCreateAPIView):
    serializer_class = WorkoutWithRecordedLogsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Workout.objects.filter(user=user).order_by('-start_timestamp')
    
    def perform_create(self, serializer):
        if 'movements' in serializer.validated_data.keys():
            initial_movements = serializer.validated_data['movements']
        else:
            initial_movements = []

        if 'template' in self.request.query_params.keys():
            try:
                workout = \
                    Workout.objects.get(id=self.request.query_params['template'])
            except Workout.DoesNotExist:
                raise ValidationError("Template workout does not exist.")
            initial_movements = workout.movements
        serializer.save(user=self.request.user, movements=initial_movements)

class WorkoutDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Workout.objects.all()
    lookup_field = 'id'
    serializer_class = WorkoutWithRecordedLogsSerializer
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
        workout.end_timestamp = timezone.now()
        workout.save()
        serializer = WorkoutSerializer(workout)
        return Response(serializer.data)
    
class WorkoutCurrent(APIView):
    permission_classes = [IsAuthenticated, IsWorkoutOwner]

    # Get the current workout, its movements' details, and each movement's most recent movement log.
    def get(self, request, format=None):
        workout = (
            Workout.objects
            .filter(user=request.user)
            .filter(end_timestamp__isnull=True)
            .order_by("-start_timestamp")
            .first()
        )
        if workout is None:
            raise Http404("Current workout does not exist.")
        
        movement_ids = workout.movements

        latest_log = MovementLog.objects.filter(movement_id=OuterRef("id")).order_by("-timestamp")
        movements = Movement.objects.filter(id__in=movement_ids).annotate(
            latest_log=Subquery(
                latest_log.annotate(
                    log=JSONObject(
                        id="id",
                        reps="reps",
                        loads="loads",
                        notes="notes",
                        timestamp="timestamp",
                        for_current_workout=Case(
                            When(workout=workout.id, then=Value(True)),
                            default=Value(False),
                            output_field=BooleanField(),
                        ),
                    )
                ).values("log")[:1],
                output_field=JSONField(),
            )
        ).order_by(
            Case(
                *[When(id=pk, then=pos) for pos, pk in enumerate(movement_ids)],
                output_field=IntegerField()
            )
        )

        workout_serializer = WorkoutWithLatestLogsSerializer(workout, context={'movements_details': movements})
        return Response(workout_serializer.data)
