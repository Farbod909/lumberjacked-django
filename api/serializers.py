from django.db.models import (
    Case, JSONField, OuterRef,
    Subquery, When, IntegerField
)

from django.db.models.functions import JSONObject
import re
from rest_framework import serializers
from .models import Movement, MovementLog, MovementLogTemplate, Workout, SET_TYPE_CHOICES


class SetSerializer(serializers.Serializer):
    reps = serializers.IntegerField(min_value=0)
    load = serializers.FloatField(required=False, allow_null=True)
    type = serializers.ChoiceField(choices=SET_TYPE_CHOICES)
    rest_time = serializers.IntegerField(min_value=0, required=False, allow_null=True)

class MovementSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Movement
        fields = [
            'id', 'author', 'name', 'notes',
            'resistance_type', 'body_part',
            'created_timestamp', 'updated_timestamp',
        ]
        read_only_fields = ['id', 'author', 'created_timestamp', 'updated_timestamp']

class MovementLogSerializer(serializers.ModelSerializer):
    movement_detail = MovementSerializer(source='movement', read_only=True)
    sets = SetSerializer(many=True)

    class Meta:
        model = MovementLog
        fields = [
            'id', 'movement', 'movement_detail', 'workout',
            'sets', 'notes', 'timestamp',
        ]
        read_only_fields = ['id']

    def validate_sets(self, value):
        if len(value) == 0:
            raise serializers.ValidationError("At least one set is required.")
        return value
    
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
            'id', 'sets', 'notes', 'timestamp', 'for_current_workout'
        ]
        read_only_fields = fields

class RecordedMovementLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovementLog
        fields = [
            'id', 'sets', 'notes', 'timestamp',
        ]
        read_only_fields = fields

class MovementWithLatestLogSerializer(serializers.ModelSerializer):
    latest_log = LatestMovementLogSerializer()
    
    class Meta:
        model = Movement
        fields = [
            'id', 'author', 'name', 'notes',
            'created_timestamp', 'updated_timestamp',
            'latest_log',
        ]
        read_only_fields = fields

class WorkoutWithLatestLogsSerializer(serializers.ModelSerializer):
    movements_details = MovementWithLatestLogSerializer(
        source="movements_details_prefetched",
        many=True,
        read_only=True
    )

    class Meta:
        model = Workout
        fields = [
            'id', 'user', 'movements_details',
            'start_timestamp', 'end_timestamp']
        read_only_fields = fields

class MovementWithRecordedLogSerializer(serializers.ModelSerializer):
    recorded_log = RecordedMovementLogSerializer()
    
    class Meta:
        model = Movement
        fields = [
            'id', 'author', 'name', 'notes',
            'created_timestamp', 'updated_timestamp',
            'recorded_log',
        ]
        read_only_fields = fields

class WorkoutWithRecordedLogsSerializer(serializers.ModelSerializer):
    movements = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )
    movements_details = MovementWithRecordedLogSerializer(
        source="movements_details_prefetched",
        many=True,
        read_only=True
    )

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

    def validate(self, attrs):
        """
        Validate that no movement with existing MovementLog is removed.
        """
        # Only check if updating an existing instance
        if self.instance is None:
            return attrs

        new_movements = attrs.get('movements', None)
        if new_movements is None:
            # movements not updated, no problem
            return attrs

        old_movements = self.instance.movements or []
        removed_movements = set(old_movements) - set(new_movements)

        if not removed_movements:
            return attrs

        # Check if any removed movement has a MovementLog for this workout
        logs_exist = MovementLog.objects.filter(
            workout=self.instance,
            movement_id__in=removed_movements
        ).exists()

        if logs_exist:
            raise serializers.ValidationError("Cannot remove movements that have associated movement logs.")

        return attrs


class TemplateSetSerializer(serializers.Serializer):
    reps = serializers.CharField()
    type = serializers.ChoiceField(choices=SET_TYPE_CHOICES)
    rest_time = serializers.IntegerField(min_value=0, required=False, allow_null=True)

    def validate_reps(self, value):
        if re.fullmatch(r'\d+', value):
            if int(value) < 1:
                raise serializers.ValidationError("Reps must be at least 1.")
        elif re.fullmatch(r'\d+-\d+', value):
            low, high = value.split('-')
            if int(low) < 1:
                raise serializers.ValidationError("Reps range minimum must be at least 1.")
            if int(low) >= int(high):
                raise serializers.ValidationError("Reps range minimum must be less than maximum.")
        else:
            raise serializers.ValidationError('Must be a number (e.g. "5") or range (e.g. "8-10").')
        return value


class MovementLogTemplateSerializer(serializers.ModelSerializer):
    sets = TemplateSetSerializer(many=True)

    class Meta:
        model = MovementLogTemplate
        fields = ['id', 'author', 'name', 'movement', 'sets']
        read_only_fields = ['id', 'author']

    def validate_sets(self, value):
        if len(value) == 0:
            raise serializers.ValidationError("At least one set is required.")
        return value

    def validate_movement(self, value):
        request = self.context.get('request')
        if value is not None and value.author != request.user:
            raise serializers.ValidationError("Movement is not owned by the authenticated user.")
        return value
