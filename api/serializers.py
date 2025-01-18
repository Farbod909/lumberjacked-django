from rest_framework import serializers
from .models import Movement, MovementLog, Workout

class MovementSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.id')
    
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
    class Meta:
        model = MovementLog
        fields = [
            'id', 'movement', 'workout',
            'reps', 'loads', 'notes', 'timestamp',
        ]
        read_only_fields = ['id', 'timestamp']

class WorkoutSerializer(serializers.ModelSerializer):
    movement_logs = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    
    class Meta:
        model = Workout
        fields = [
            'id', 'user', 'movements', 'movement_logs',
            'start_timestamp', 'end_timestamp']
        read_only_fields = ['id', 'user', 'start_timestamp', 'end_timestamp']
