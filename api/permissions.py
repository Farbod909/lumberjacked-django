from rest_framework import permissions


class IsMovementOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user

class IsMovementLogOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.workout_movement.workout.user == request.user

class IsWorkoutOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class IsWorkoutMovementOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.workout.user == request.user

class IsMovementLogTemplateOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user
