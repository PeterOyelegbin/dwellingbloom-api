from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import ConversationViewSet

router = DefaultRouter()
router.register(r"conversations", ConversationViewSet, basename="conversation")

urlpatterns = router.urls

# urlpatterns = [
#     path('conversations', ConversationViewSet.as_view({'get': 'get_queryset', 'post': 'create'}), name='conversations'),
#     path('conversations/<uuid:id>', ConversationViewSet.as_view({'get': 'messages', 'post': 'messages'}), name='conversation-detail'),
#     path('conversations/<uuid:id>/mark-read', ConversationViewSet.as_view({'post': 'mark_read'}), name='conversation-mark-read'),
#     path('conversations/<uuid:id>/messages', ConversationViewSet.as_view({'get': 'messages', 'post': 'messages'}), name='messages'),
# ]
