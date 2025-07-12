from rest_framework import serializers
from .models import SessionHistory, OutfitAnalysis, Prompt

class OutfitAnalysisSerializer(serializers.ModelSerializer):
    colors_display = serializers.SerializerMethodField()
    bullet_advice_display = serializers.SerializerMethodField()
    
    class Meta:
        model = OutfitAnalysis
        fields = ['id', 'title', 'colors', 'colors_display', 'description', 
                 'advice', 'bullet_advice', 'bullet_advice_display', 'image', 
                 'created_at', 'session_id']
        read_only_fields = ['id', 'created_at', 'session_id']
    
    def get_colors_display(self, obj):
        return obj.get_colors_display()
    
    def get_bullet_advice_display(self, obj):
        return obj.get_bullet_advice_display()

class SessionHistorySerializer(serializers.ModelSerializer):
    analysis_data_display = serializers.SerializerMethodField()
    
    class Meta:
        model = SessionHistory
        fields = ['id', 'session_id', 'user_input', 'response', 'image', 
                 'analysis_data', 'analysis_data_display', 'timestamp']
        read_only_fields = ['id', 'timestamp', 'session_id']
    
    def get_analysis_data_display(self, obj):
        return obj.get_analysis_data()

class ChatRequestSerializer(serializers.Serializer):
    query = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False)
    session_id = serializers.CharField(required=False)
    
    def validate(self, attrs):
        query = attrs.get('query', '').strip()
        image = attrs.get('image')
        
        if not query and not image:
            raise serializers.ValidationError("Must provide either query or image")
        
        return attrs

class OutfitAnalysisRequestSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)
    
    def validate_image(self, value):
        # Validate file size (limit to 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image size exceeds 5MB limit")
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Only JPEG and PNG images are allowed")
        
        return value

class TextQuerySerializer(serializers.Serializer):
    query = serializers.CharField(required=True)
    session_id = serializers.CharField(required=False)

# from rest_framework import serializers
# from .models import SessionHistory

# class OutfitAnalysisRequestSerializer(serializers.Serializer):
#     image = serializers.ImageField()
#     context = serializers.CharField(required=False, allow_blank=True)
#     user_id = serializers.CharField(max_length=100)  # New field for user ID

# class OutfitAnalysisResponseSerializer(serializers.Serializer):
#     title = serializers.CharField(max_length=50)
#     colors = serializers.ListField(child=serializers.CharField())
#     description = serializers.CharField()
#     advice = serializers.CharField()

# class TextQueryRequestSerializer(serializers.Serializer):
#     query = serializers.CharField()
#     user_id = serializers.CharField(max_length=100)  # New field for user ID

# class SessionHistorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SessionHistory
#         fields = ['user_id', 'user_input', 'response', 'timestamp', 'image']


class PromptSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Prompt
        fields = '__all__'