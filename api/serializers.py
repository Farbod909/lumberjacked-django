import re
from rest_framework import serializers
from .models import Movement, MovementLog, MovementLogTemplate, Workout, WorkoutMovement, SET_TYPE_CHOICES


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
    movement_detail = MovementSerializer(source='workout_movement.movement', read_only=True)
    sets = SetSerializer(many=True)

    class Meta:
        model = MovementLog
        fields = ['id', 'workout_movement', 'movement_detail', 'sets', 'notes', 'timestamp']
        read_only_fields = ['id']

    def validate_sets(self, value):
        if len(value) == 0:
            raise serializers.ValidationError("At least one set is required.")
        return value

    def validate_workout_movement(self, value):
        request = self.context.get('request')
        if value.workout.user != request.user:
            raise serializers.ValidationError("Workout movement is not owned by the authenticated user.")
        return value


class WorkoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workout
        fields = ['id', 'user', 'start_timestamp', 'end_timestamp']
        read_only_fields = ['id', 'user', 'start_timestamp', 'end_timestamp']


class RecordedMovementLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovementLog
        fields = ['id', 'sets', 'notes', 'timestamp']
        read_only_fields = fields


class LatestMovementLogSerializer(serializers.ModelSerializer):
    for_current_workout = serializers.BooleanField()

    class Meta:
        model = MovementLog
        fields = ['id', 'sets', 'notes', 'timestamp', 'for_current_workout']
        read_only_fields = fields


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


class WorkoutMovementSerializer(serializers.ModelSerializer):
    movement_detail = MovementSerializer(source='movement', read_only=True)
    template_detail = MovementLogTemplateSerializer(source='template', read_only=True)

    class Meta:
        model = WorkoutMovement
        fields = ['id', 'workout', 'movement', 'movement_detail', 'template', 'template_detail', 'order']
        read_only_fields = ['id', 'order']


class WorkoutMovementWithRecordedLogSerializer(serializers.ModelSerializer):
    """
    Flattens movement fields to the top level to preserve the pre-WorkoutMovement
    API shape, adding workout_movement_id for client reference.
    """
    class Meta:
        model = WorkoutMovement
        fields = ['id']

    def to_representation(self, instance):
        movement_data = MovementSerializer(instance.movement, context=self.context).data
        try:
            recorded_log = RecordedMovementLogSerializer(instance.movement_log).data
        except MovementLog.DoesNotExist:
            recorded_log = None
        return {
            'workout_movement_id': instance.id,
            **movement_data,
            'recorded_log': recorded_log,
        }


class WorkoutMovementWithLatestLogSerializer(serializers.ModelSerializer):
    """
    Like WorkoutMovementWithRecordedLogSerializer but shows the most recent log
    for the movement across all workouts, with a for_current_workout flag.
    Also includes the selected template.
    """
    class Meta:
        model = WorkoutMovement
        fields = ['id']

    def to_representation(self, instance):
        movement_data = MovementSerializer(instance.movement, context=self.context).data
        template_data = MovementLogTemplateSerializer(instance.template, context=self.context).data if instance.template else None

        try:
            log = instance.movement_log
            log.for_current_workout = True
        except MovementLog.DoesNotExist:
            log = (
                MovementLog.objects
                .filter(workout_movement__movement=instance.movement)
                .order_by('-timestamp')
                .first()
            )
            if log:
                log.for_current_workout = False

        return {
            'workout_movement_id': instance.id,
            'template': template_data,
            **movement_data,
            'latest_log': LatestMovementLogSerializer(log).data if log else None,
        }


class WorkoutWithRecordedLogsSerializer(serializers.ModelSerializer):
    movements = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    movements_details = serializers.SerializerMethodField()

    class Meta:
        model = Workout
        fields = ['id', 'user', 'movements', 'movements_details', 'start_timestamp', 'end_timestamp']
        read_only_fields = ['id', 'user', 'movements_details', 'start_timestamp', 'end_timestamp']

    def get_movements_details(self, obj):
        wms = obj.workout_movements.all()
        return WorkoutMovementWithRecordedLogSerializer(wms, many=True, context=self.context).data

    def validate(self, attrs):
        if self.instance is None:
            return attrs

        new_movement_ids = attrs.get('movements')
        if new_movement_ids is None:
            return attrs

        old_movement_ids = set(self.instance.workout_movements.values_list('movement_id', flat=True))
        removed = old_movement_ids - set(new_movement_ids)

        if removed and WorkoutMovement.objects.filter(
            workout=self.instance,
            movement_id__in=removed,
            id__in=MovementLog.objects.values('workout_movement_id'),
        ).exists():
            raise serializers.ValidationError("Cannot remove movements that have associated movement logs.")

        return attrs

    def create(self, validated_data):
        movement_ids = validated_data.pop('movements', [])
        workout = super().create(validated_data)
        for order, movement_id in enumerate(movement_ids):
            WorkoutMovement.objects.create(workout=workout, movement_id=movement_id, order=order)
        return workout

    def update(self, instance, validated_data):
        movement_ids = validated_data.pop('movements', None)
        instance = super().update(instance, validated_data)

        if movement_ids is not None:
            existing = {wm.movement_id: wm for wm in instance.workout_movements.all()}
            removed = set(existing.keys()) - set(movement_ids)
            instance.workout_movements.filter(movement_id__in=removed).delete()

            for order, mid in enumerate(movement_ids):
                if mid in existing:
                    wm = existing[mid]
                    if wm.order != order:
                        wm.order = order
                        wm.save(update_fields=['order'])
                else:
                    WorkoutMovement.objects.create(workout=instance, movement_id=mid, order=order)

        return instance


class WorkoutWithLatestLogsSerializer(serializers.ModelSerializer):
    movements_details = serializers.SerializerMethodField()

    class Meta:
        model = Workout
        fields = ['id', 'user', 'movements_details', 'start_timestamp', 'end_timestamp']
        read_only_fields = fields

    def get_movements_details(self, obj):
        wms = obj.workout_movements.select_related('movement', 'template', 'movement_log').order_by('order')
        return WorkoutMovementWithLatestLogSerializer(wms, many=True, context=self.context).data
