"""Rides views."""

# Django
from django.utils import timezone
# DRF
from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.filters import (
    SearchFilter,
    OrderingFilter,
)
# Permissions
from rest_framework.permissions import IsAuthenticated
# Utilities
from datetime import timedelta

# Serializers
from cride.rides.serializers import (
    CreateRideSerializer,
    RideModelSerializer,
    JoinRideSerializer,
)
# Models
from cride.circles.models import Circle
# Views
from cride.utils.views import RelatedToCircle
# Permissions
from cride.circles.permissions.memberships import IsActiveCircleMember
from cride.rides.permissions import IsRideOwner

class RideViewSet(
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.UpdateModelMixin,
        viewsets.GenericViewSet,
    ):
    """Rides view set."""

    permission_classes = [IsAuthenticated, IsActiveCircleMember]
    filter_backends = (SearchFilter, OrderingFilter)
    ordering = ('departure_date', 'arrival_date', 'available_seats')
    ordering_fields = ('departure_date', 'arrival_date', 'available_seats')
    search_fields = ('departure_location', 'arrival_location')

    def dispatch(self, request, *args, **kwargs):
        """Verify that the circle exists."""

        slug_name = kwargs['slug_name']

        self.circle = get_object_or_404(
            Circle,
            slug_name=slug_name,
        )

        return super(RideViewSet, self).dispatch(request, *args, **kwargs)

    def get_permissions(self):
        """Assign permission based on action."""
        permissions = [IsAuthenticated, IsActiveCircleMember]

        if self.action in ['partial_update', 'update']:
            permissions.append(IsRideOwner)

        return [p() for p in permissions]

    def get_serializer_context(self):
        """Add circle to serializer context."""
        context = super(RideViewSet, self).get_serializer_context()

        context['circle'] = self.circle

        return context

    def get_serializer_class(self):
        """Return serializer based on action."""

        serializer_class = RideModelSerializer

        if self.action == 'create':
            serializer_class = CreateRideSerializer
        elif self.action == 'update':
            serializer_class = JoinRideSerializer

        return serializer_class

    def get_queryset(self):
        """Return active circles rides."""

        offset = timezone.now() + timedelta(minutes=10)

        return self.circle.ride_set.filter(
            departure_date__gte=offset,
            is_active=True,
            available_seats__gte=1,
        )

    @action(detail=True, methods=['POST'])
    def join(self, request, *args, **kwargs):
        """Add requesting user to ride."""

        ride = self.get_object()
        serializer = JoinRideSerializer(
            ride,
            data={'passenger': request.user.pk},
            context={'ride': ride, 'circle': self.circle},
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        ride = serializer.save()
        data = RideModelSerializer(ride).data
        return Response(data, status=status.HTTP_200_OK)