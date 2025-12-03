"""
URL routes for the emails API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'emails', views.EmailViewSet, basename='email')

urlpatterns = [
    # REST API routes
    path('', include(router.urls)),
    
    # Webhook endpoint
    path('webhook/email/', views.webhook_email, name='webhook-email'),
    
    # Connection management
    path('connect/', views.initiate_connection, name='initiate-connection'),
    path('connect/complete/', views.complete_connection, name='complete-connection'),
    path('connect/status/', views.connection_status, name='connection-status'),
    
    # Manual sync
    path('sync/', views.sync_emails, name='sync-emails'),
]

