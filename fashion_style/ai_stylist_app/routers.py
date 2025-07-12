from rest_framework import routers
from .views import PromptViewSet

ai_stylist_router = routers.SimpleRouter()
ai_stylist_router.register(r'prompt', PromptViewSet, basename='prompt')