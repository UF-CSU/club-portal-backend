"""
Views for the links API.
"""

from django.urls import reverse_lazy
from analytics.models import Link
from core.abstracts.viewsets import ModelViewSetBase, ViewSetBase
from rest_framework import authentication, generics, mixins, permissions
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.settings import api_settings
from django.shortcuts import get_object_or_404

from analytics.serializers import LinkSerializer

class LinkViewSet(ModelViewSetBase):
    """CRUD Api routes for Link models"""

    serializer_class = LinkSerializer


    queryset = Link.objects.all()

    
# def get_queryset(self):
#         qs = Link.objects.all()
#         club_id = self.kwargs.get("id", None)
# 
#         if club_id is not None:
#             try:
#                 club_id = int(club_id)
#             except:
#                 return self.queryset.none()
#         
#         self.queryset = self.queryset.filter(club__id=club_id)
# 
#         return get_object_or_404(self.queryset)

