from django.contrib import admin

from .models import Movement, MovementLog, Workout

admin.site.register(Movement)
admin.site.register(MovementLog)
admin.site.register(Workout)