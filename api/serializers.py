from django.db.models import (
    Case, JSONField, OuterRef,
    Subquery, When, IntegerField
)

from django.db.models.functions import JSONObject
from rest_framework import serializers
from .models import Movement, MovementLog, Workout

class MovementSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Movement
        fields = [
            'id', 'author', 'name', 'category', 'notes',
            'created_timestamp', 'updated_timestamp',
            'recommended_warmup_sets', 'recommended_working_sets',
            'recommended_rep_range', 'recommended_rpe', 
            'recommended_rest_time',
        ]
        read_only_fields = ['id', 'author', 'created_timestamp', 'updated_timestamp']

class MovementLogSerializer(serializers.ModelSerializer):
    movement_detail = MovementSerializer(source='movement', read_only=True)

    class Meta:
        model = MovementLog
        fields = [
            'id', 'movement', 'movement_detail', 'workout',
            'reps', 'loads', 'notes', 'timestamp',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        # Ensure reps and loads have same length.
        reps = []
        loads = []
        if self.instance:
            if self.instance.reps:
                reps = self.instance.reps
            if self.instance.loads:
                loads = self.instance.loads
        if 'reps' in data:
            reps = data['reps']
        if 'loads' in data:
            loads = data['loads']

        if len(reps) != len(loads):
            raise serializers.ValidationError("reps and loads must have the same length.")
        return data
    
class WorkoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workout
        fields = [
            'id', 'user', 'movements', 'movement_logs',
            'start_timestamp', 'end_timestamp']
        read_only_fields = [
            'id', 'user', 'movement_logs',
            'start_timestamp', 'end_timestamp']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['movement_logs'] = MovementLogSerializer(instance.movement_logs, many=True).data
        return representation

class LatestMovementLogSerializer(serializers.ModelSerializer):
    for_current_workout = serializers.BooleanField()

    class Meta:
        model = MovementLog
        fields = [
            'id', 'reps', 'loads', 'notes', 'timestamp', 'for_current_workout'
        ]
        read_only_fields = fields

class RecordedMovementLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovementLog
        fields = [
            'reps', 'loads', 'notes', 'timestamp',
        ]
        read_only_fields = fields

class MovementWithLatestLogSerializer(serializers.ModelSerializer):
    latest_log = LatestMovementLogSerializer()
    
    class Meta:
        model = Movement
        fields = [
            'id', 'author', 'name', 'category', 'notes',
            'created_timestamp', 'updated_timestamp',
            'recommended_warmup_sets', 'recommended_working_sets',
            'recommended_rep_range', 'recommended_rpe', 
            'recommended_rest_time', 'latest_log',
        ]
        read_only_fields = fields

class WorkoutWithLatestLogsSerializer(serializers.ModelSerializer):
    movements_details = serializers.SerializerMethodField()

    class Meta:
        model = Workout
        fields = [
            'id', 'user', 'movements_details',
            'start_timestamp', 'end_timestamp']
        read_only_fields = fields

    def get_movements_details(self, obj):
        movements_details = self.context.get('movements_details', [])
        return MovementWithLatestLogSerializer(movements_details, many=True).data

class MovementWithRecordedLogSerializer(serializers.ModelSerializer):
    recorded_log = RecordedMovementLogSerializer()
    
    class Meta:
        model = Movement
        fields = [
            'id', 'author', 'name', 'category', 'notes',
            'created_timestamp', 'updated_timestamp',
            'recommended_warmup_sets', 'recommended_working_sets',
            'recommended_rep_range', 'recommended_rpe', 
            'recommended_rest_time', 'recorded_log',
        ]
        read_only_fields = fields

class WorkoutWithRecordedLogsSerializer(serializers.ModelSerializer):
    movements_details = serializers.SerializerMethodField()

    class Meta:
        model = Workout
        fields = [
            'id', 'user', 'movements', 'movements_details',
            'start_timestamp', 'end_timestamp'
        ]
        read_only_fields = [
            'id', 'user', 'movements_details',
            'start_timestamp', 'end_timestamp'
        ]

    def get_movements_details(self, obj):
        movement_ids = obj.movements

        recorded_log = MovementLog.objects.filter(
            movement_id=OuterRef("id"),
            workout_id=obj.id
        ).annotate(
            log=JSONObject(
                reps="reps",
                loads="loads",
                notes="notes",
                timestamp="timestamp",
            )
        ).values("log")[:1]

        movements = Movement.objects.filter(id__in=movement_ids).annotate(
            recorded_log=Subquery(recorded_log, output_field=JSONField())
        ).order_by(
            Case(
                *[When(id=pk, then=pos) for pos, pk in enumerate(movement_ids)],
                output_field=IntegerField()
            )
        )

        return MovementWithRecordedLogSerializer(movements, many=True).data
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        del representation['movements']
        return representation
