from django.urls import path
from . import views

urlpatterns = [
    # Main AI endpoints
    path('analyze-outfit/', views.OutfitAnalysisView.as_view(), name='analyze-outfit'),
    path('text-query/', views.TextQueryView.as_view(), name='text-query'),
    path('chat/', views.ChatView.as_view(), name='ai-chat'),
    
    # User history endpoints
    path('outfit-history/', views.UserOutfitHistoryView.as_view(), name='outfit-history'),
    path('conversation-history/', views.UserConversationHistoryView.as_view(), name='conversation-history'),
    path('outfit-analysis/<int:pk>/', views.OutfitAnalysisDetailView.as_view(), name='outfit-analysis-detail'),
]

# from django.urls import path
# from .views import OutfitAnalysisView, TextQueryView

# app_name = 'ai_stylist'

# urlpatterns = [
#     path('analyze-outfit/', OutfitAnalysisView.as_view(), name='analyze-outfit'),
#     path('text-query/', TextQueryView.as_view(), name='text-query'),
# ]