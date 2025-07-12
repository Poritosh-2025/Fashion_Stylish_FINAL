from django.contrib import admin
from .models import SessionHistory, OutfitAnalysis, Prompt

@admin.register(SessionHistory)
class SessionHistoryAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user_id', 'user_input', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['session_id', 'user_id', 'user_input']
    readonly_fields = ['session_id', 'timestamp']
    ordering = ['-timestamp']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related()

@admin.register(OutfitAnalysis)
class OutfitAnalysisAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'get_colors_display', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'description', 'user__email']
    readonly_fields = ['session_id', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')
    

admin.site.register(Prompt)
