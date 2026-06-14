import re
from rest_framework import serializers
from .models import (
    Movement, MovementLog, MovementLogTemplate,
    Workout, WorkoutMovement, WorkoutTemplate, WorkoutTemplateMovement,
    SET_TYPE_CHOICES,
)


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
    template = serializers.PrimaryKeyRelatedField(
        queryset=WorkoutTemplate.objects.all(), write_only=True, required=False, allow_null=True
    )
    movements_details = serializers.SerializerMethodField()

    class Meta:
        model = Workout
        fields = ['id', 'user', 'movements', 'template', 'movements_details', 'start_timestamp', 'end_timestamp']
        read_only_fields = ['id', 'user', 'movements_details', 'start_timestamp', 'end_timestamp']

    def get_movements_details(self, obj):
        wms = obj.workout_movements.all()
        return WorkoutMovementWithRecordedLogSerializer(wms, many=True, context=self.context).data

    def validate(self, attrs):
        # Mutual exclusion of template and movements
        if attrs.get('template') and attrs.get('movements'):
            raise serializers.ValidationError(
                "Provide either template or movements, not both."
            )

        if self.instance is None:
            # Validate template movements are still owned by the user
            template = attrs.get('template')
            if template:
                request = self.context.get('request')
                for tm in template.template_movements.select_related('movement').order_by('order'):
                    if not Movement.objects.filter(id=tm.movement_id, author=request.user).exists():
                        raise serializers.ValidationError(
                            {"template": f"Movement '{tm.movement.name}' no longer exists or is not owned by you."}
                        )
            return attrs

        # Update only: prevent removing movements with logs
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
        template = validated_data.pop('template', None)
        movement_ids = validated_data.pop('movements', [])
        workout = super().create(validated_data)

        if template:
            for tm in template.template_movements.select_related('movement', 'movement_log_template').order_by('order'):
                WorkoutMovement.objects.create(
                    workout=workout,
                    movement=tm.movement,
                    template=tm.movement_log_template,
                    order=tm.order,
                )
        else:
            for order, movement_id in enumerate(movement_ids):
                WorkoutMovement.objects.create(workout=workout, movement_id=movement_id, order=order)

        return workout

    def update(self, instance, validated_data):
        validated_data.pop('template', None)
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


class WorkoutTemplateMovementItemSerializer(serializers.Serializer):
    """Write-only serializer for each movement item in a WorkoutTemplate."""
    movement = serializers.PrimaryKeyRelatedField(queryset=Movement.objects.all())
    movement_log_template = serializers.PrimaryKeyRelatedField(
        queryset=MovementLogTemplate.objects.all(), required=False, allow_null=True
    )


class WorkoutTemplateMovementSerializer(serializers.ModelSerializer):
    """Read-only serializer showing movement + template details within a WorkoutTemplate."""
    movement_detail = MovementSerializer(source='movement', read_only=True)
    movement_log_template_detail = MovementLogTemplateSerializer(source='movement_log_template', read_only=True)

    class Meta:
        model = WorkoutTemplateMovement
        fields = [
            'id', 'movement', 'movement_detail',
            'movement_log_template', 'movement_log_template_detail',
            'order',
        ]
        read_only_fields = fields


class WorkoutTemplateSerializer(serializers.ModelSerializer):
    movements = WorkoutTemplateMovementItemSerializer(many=True, write_only=True, required=False)
    source_workout = serializers.PrimaryKeyRelatedField(
        queryset=Workout.objects.all(), write_only=True, required=False, allow_null=True
    )
    movements_details = serializers.SerializerMethodField()

    class Meta:
        model = WorkoutTemplate
        fields = [
            'id', 'author', 'name', 'source_workout', 'movements',
            'movements_details', 'created_timestamp', 'updated_timestamp',
        ]
        read_only_fields = ['id', 'author', 'movements_details', 'created_timestamp', 'updated_timestamp']

    def get_movements_details(self, obj):
        wms = obj.template_movements.select_related('movement', 'movement_log_template').order_by('order')
        return WorkoutTemplateMovementSerializer(wms, many=True, context=self.context).data

    def validate(self, attrs):
        request = self.context.get('request')
        source_workout = attrs.get('source_workout')
        movements = attrs.get('movements')

        if self.instance is None:
            if source_workout and movements is not None:
                raise serializers.ValidationError(
                    "Provide either source_workout or movements, not both."
                )
            if source_workout is None and movements is None:
                raise serializers.ValidationError(
                    "Either source_workout or movements must be provided."
                )

        if source_workout and source_workout.user != request.user:
            raise serializers.ValidationError(
                {"source_workout": "Workout is not owned by the authenticated user."}
            )

        name = attrs.get('name')
        if name:
            qs = WorkoutTemplate.objects.filter(author=request.user, name=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "A template with this name already exists."}
                )

        if movements:
            for item in movements:
                movement = item['movement']
                if movement.author != request.user:
                    raise serializers.ValidationError(
                        {"movements": f"Movement '{movement.name}' is not owned by the authenticated user."}
                    )
                mlt = item.get('movement_log_template')
                if mlt and mlt.author != request.user:
                    raise serializers.ValidationError(
                        {"movements": f"Movement log template '{mlt.name}' is not owned by the authenticated user."}
                    )

        return attrs

    def create(self, validated_data):
        source_workout = validated_data.pop('source_workout', None)
        movements_data = validated_data.pop('movements', None)
        template = super().create(validated_data)

        if source_workout:
            for wm in source_workout.workout_movements.select_related('movement', 'template').order_by('order'):
                WorkoutTemplateMovement.objects.create(
                    template=template,
                    movement=wm.movement,
                    movement_log_template=wm.template,
                    order=wm.order,
                )
        else:
            for order, item in enumerate(movements_data):
                WorkoutTemplateMovement.objects.create(
                    template=template,
                    movement=item['movement'],
                    movement_log_template=item.get('movement_log_template'),
                    order=order,
                )

        return template

    def update(self, instance, validated_data):
        validated_data.pop('source_workout', None)
        movements_data = validated_data.pop('movements', None)
        instance = super().update(instance, validated_data)

        if movements_data is not None:
            instance.template_movements.all().delete()
            for order, item in enumerate(movements_data):
                WorkoutTemplateMovement.objects.create(
                    template=instance,
                    movement=item['movement'],
                    movement_log_template=item.get('movement_log_template'),
                    order=order,
                )

        return instance
