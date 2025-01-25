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
    movement_logs = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    
    class Meta:
        model = Workout
        fields = [
            'id', 'user', 'movements', 'movement_logs',
            'start_timestamp', 'end_timestamp']
        read_only_fields = ['id', 'user', 'start_timestamp', 'end_timestamp']
