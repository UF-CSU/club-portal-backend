"""
Views for the links API.
"""

from django.urls import reverse_lazy
from analytics.models import Link, QRCode
from clubs import serializers
from core.abstracts.viewsets import ModelViewSetBase, ViewSetBase
import querycsv
from rest_framework import authentication, generics, mixins, permissions
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.settings import api_settings
from django.shortcuts import get_object_or_404

from analytics.serializers import LinkSerializer, QrSerializer

class LinkViewSet(ModelViewSetBase):
    """CRUD Api routes for Link models"""

    serializer_class = LinkSerializer

    queryset = Link.objects.all()
    
    @action(detail=False, methods = ['get', 'delete'], url_path=r'club/(?P<id>\d+)')
    def filter_by_club(self, request, id=None):
    
        if id is not None:
            try:
                id = int(id)
            except:
                return self.queryset.none()
        
        qs = self.queryset.filter(club__id=id)
    
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class QrViewSet(ModelViewSetBase):
    """CRUD Api routes for QR models"""

    serializer_class = QrSerializer

    queryset = QRCode.objects.all()