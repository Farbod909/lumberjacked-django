from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from authn.models import User
from lumberjacked.utils import generate_id

SET_TYPE_CHOICES = ['warmup', 'working', 'failure', 'myoreps']

class Movement(models.Model):
    id = models.PositiveBigIntegerField(default=generate_id, primary_key=True, editable=False)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200, blank=False)
    category = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_timestamp = models.DateTimeField(auto_now_add=True)
    updated_timestamp = models.DateTimeField(auto_now=True)

    recommended_warmup_sets = models.CharField(max_length=7, blank=True)
    recommended_working_sets = models.CharField(max_length=7, blank=True)
    recommended_rep_range = models.CharField(max_length=7, blank=True)
    recommended_rpe = models.CharField(max_length=7, blank=True)
    recommended_rest_time = models.PositiveSmallIntegerField(blank=True, null=True)

    def __str__(self):
        return "Movement (name: %s, user: %s)" % (self.name, self.author)
    
class Workout(models.Model):
    id = models.PositiveBigIntegerField(default=generate_id, primary_key=True, editable=False)
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    movements = ArrayField(models.PositiveBigIntegerField(), default=list)
    start_timestamp = models.DateTimeField(auto_now_add=True)
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


class MovementLog(models.Model):
    id = models.PositiveBigIntegerField(default=generate_id, primary_key=True, editable=False)
    movement = models.ForeignKey(Movement, on_delete=models.CASCADE, related_name='movement_logs')
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='movement_logs')
    # Each element: {reps: int, load: float|null, type: "warmup"|"working"|"failure"|"myoreps", rest_time: int|null}
    # Structure is enforced by SetSerializer.
    sets = models.JSONField(default=list)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(blank=True, default=timezone.now)

    def __str__(self):
        return "MovementLog (movement: %s, date: %s)" % (self.movement, self.timestamp.date())
