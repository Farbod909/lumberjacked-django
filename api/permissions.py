from rest_framework import permissions


class IsMovementOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a Movement to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Write permissions are only allowed to the owner of the snippet.
        return obj.author == request.user

class IsMovementLogOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a MovementLog to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Write permissions are only allowed to the owner of the snippet.
        return obj.workout.user == request.user

class IsWorkoutOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a Workout to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Write permissions are only allowed to the owner of the snippet.
        return obj.user == request.user
