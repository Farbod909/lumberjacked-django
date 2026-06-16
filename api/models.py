from django.db import models
from django.utils import timezone

from authn.models import User
from lumberjacked.utils import generate_id

SET_TYPE_CHOICES = ['warmup', 'working', 'failure', 'myoreps']


class ResistanceType(models.TextChoices):
    BODYWEIGHT      = 'bodyweight',      'Bodyweight'
    DUMBBELL        = 'dumbbell',        'Dumbbell'
    BARBELL         = 'barbell',         'Barbell'
    MACHINE         = 'machine',         'Machine'
    CABLE           = 'cable',           'Cable'
    KETTLEBELL      = 'kettlebell',      'Kettlebell'
    RESISTANCE_BAND = 'resistance_band', 'Resistance Band'
    MEDICINE_BALL   = 'medicine_ball',   'Medicine Ball'
    SMITH_MACHINE   = 'smith_machine',   'Smith Machine'
    SUSPENSION_TRX  = 'suspension_trx',  'Suspension (TRX)'
    FIXED_BARBELL   = 'fixed_barbell',   'Fixed Barbell'
    WEIGHTED_VEST   = 'weighted_vest',   'Weighted Vest'
    SANDBAG         = 'sandbag',         'Sandbag'
    BELT_ATTACHED   = 'belt_attached',   'Belt-attached'
    DIGITAL         = 'digital',         'Digital'
    OTHER           = 'other',           'Other'


class BodyPart(models.TextChoices):
    # Broad
    FULL_BODY           = 'full_body',           'Full Body'
    UPPER_BODY          = 'upper_body',          'Upper Body'
    LOWER_BODY          = 'lower_body',          'Lower Body'
    CORE                = 'core',                'Core'
    # Groups
    CHEST               = 'chest',               'Chest'
    BACK                = 'back',                'Back'
    SHOULDERS           = 'shoulders',           'Shoulders'
    ARMS                = 'arms',                'Arms'
    GLUTES              = 'glutes',              'Glutes'
    QUADS               = 'quads',               'Quads'
    HAMSTRINGS          = 'hamstrings',          'Hamstrings'
    CALVES              = 'calves',              'Calves'
    HIP_FLEXORS         = 'hip_flexors',         'Hip Flexors'
    ADDUCTORS           = 'adductors',           'Adductors'
    ABDUCTORS           = 'abductors',           'Abductors'
    # Specific
    UPPER_CHEST         = 'upper_chest',         'Upper Chest'
    LOWER_CHEST         = 'lower_chest',         'Lower Chest'
    LATS                = 'lats',                'Lats'
    TRAPS               = 'traps',               'Traps'
    RHOMBOIDS           = 'rhomboids',           'Rhomboids'
    LOWER_BACK          = 'lower_back',          'Lower Back'
    FRONT_DELTS         = 'front_delts',         'Front Delts'
    SIDE_DELTS          = 'side_delts',          'Side Delts'
    REAR_DELTS          = 'rear_delts',          'Rear Delts'
    BICEPS              = 'biceps',              'Biceps'
    TRICEPS             = 'triceps',             'Triceps'
    FOREARMS            = 'forearms',            'Forearms'
    GLUTE_MAX           = 'glute_max',           'Glute Max'
    GLUTE_MED           = 'glute_med',           'Glute Med'
    GASTROCNEMIUS       = 'gastrocnemius',       'Gastrocnemius'
    SOLEUS              = 'soleus',              'Soleus'
    RECTUS_ABDOMINIS    = 'rectus_abdominis',    'Rectus Abdominis'
    OBLIQUES            = 'obliques',            'Obliques'
    TRANSVERSE_ABDOMINIS = 'transverse_abdominis', 'Transverse Abdominis'


class Movement(models.Model):
    id = models.PositiveBigIntegerField(default=generate_id, primary_key=True, editable=False)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200, blank=False)
    notes = models.TextField(blank=True)
    resistance_type = models.CharField(max_length=20, blank=True, choices=ResistanceType.choices)
    body_part = models.CharField(max_length=25, blank=True, choices=BodyPart.choices)
    created_timestamp = models.DateTimeField(auto_now_add=True)
    updated_timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Movement (name: %s, user: %s)" % (self.name, self.author)


class Workout(models.Model):
    id = models.PositiveBigIntegerField(default=generate_id, primary_key=True, editable=False)
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    start_timestamp = models.DateTimeField(default=timezone.now)
    end_timestamp = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return "Workout (date: %s, user: %s)" % (self.start_timestamp.date(), self.user)


class MovementLogTemplate(models.Model):
    id = models.PositiveBigIntegerField(default=generate_id, primary_key=True, editable=False)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200, blank=False)
    movement = models.ForeignKey('Movement', null=True, blank=True, on_delete=models.SET_NULL, related_name='templates')
    # Each element: {reps: str ("5" or "8-10"), type: "warmup"|"working"|"failure"|"myoreps", rest_time: int|null}
    # Structure is enforced by TemplateSetSerializer.
    sets = models.JSONField(default=list)

    def __str__(self):
        return "MovementLogTemplate (name: %s, user: %s)" % (self.name, self.author)


class WorkoutTemplate(models.Model):
    id = models.PositiveBigIntegerField(default=generate_id, primary_key=True, editable=False)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200, blank=False)
    created_timestamp = models.DateTimeField(auto_now_add=True)
    updated_timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('author', 'name')]

    def __str__(self):
        return "WorkoutTemplate (name: %s, user: %s)" % (self.name, self.author)


class WorkoutTemplateMovement(models.Model):
    id = models.PositiveBigIntegerField(default=generate_id, primary_key=True, editable=False)
    template = models.ForeignKey(WorkoutTemplate, on_delete=models.CASCADE, related_name='template_movements')
    movement = models.ForeignKey(Movement, on_delete=models.CASCADE)
    movement_log_template = models.ForeignKey(MovementLogTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return "WorkoutTemplateMovement (movement: %s, template: %s, order: %s)" % (self.movement, self.template, self.order)


class WorkoutMovement(models.Model):
    id = models.PositiveBigIntegerField(default=generate_id, primary_key=True, editable=False)
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='workout_movements')
    movement = models.ForeignKey(Movement, on_delete=models.CASCADE, related_name='workout_movements')
    template = models.ForeignKey(MovementLogTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return "WorkoutMovement (movement: %s, workout: %s, order: %s)" % (self.movement, self.workout, self.order)


class MovementLog(models.Model):
    id = models.PositiveBigIntegerField(default=generate_id, primary_key=True, editable=False)
    workout_movement = models.OneToOneField(WorkoutMovement, on_delete=models.CASCADE, related_name='movement_log')
    # Each element: {reps: int, load: float|null, type: "warmup"|"working"|"failure"|"myoreps", rest_time: int|null}
    # Structure is enforced by SetSerializer.
    sets = models.JSONField(default=list)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(blank=True, default=timezone.now)

    def __str__(self):
        return "MovementLog (movement: %s, date: %s)" % (self.workout_movement.movement, self.timestamp.date())
