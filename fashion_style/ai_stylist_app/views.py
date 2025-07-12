
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from uuid import uuid4
import json
from datetime import datetime

from .permissions import AdminOrReadOnly

from .models import SessionHistory, OutfitAnalysis, Prompt
from .serializers import (
    OutfitAnalysisSerializer, 
    SessionHistorySerializer, 
    ChatRequestSerializer,
    OutfitAnalysisRequestSerializer,
    TextQuerySerializer,
    PromptSerializer
)
from .utils import (
    analyze_outfit_with_ai, 
    handle_text_query_with_ai, 
    save_session_history,
    update_user_fields,
    PHOTO_PROMPT,
    SYSTEM_PROMPT
)

User = get_user_model()

class OutfitAnalysisView(APIView):
    """
    API endpoint for outfit analysis (Main Page)
    POST /api/ai/analyze-outfit/
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        try:
            serializer = OutfitAnalysisRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            image_file = serializer.validated_data['image']
            session_id = str(uuid4())
            user_id = request.user.id if request.user.is_authenticated else None
            
            # Analyze outfit with AI
            analysis_result = analyze_outfit_with_ai(image_file, session_id, user_id)
            
            # Save outfit analysis to database
            outfit_analysis = OutfitAnalysis.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=session_id,
                image=image_file,
                title=analysis_result['title'],
                colors=analysis_result['colors'],
                description=analysis_result['description'],
                advice=analysis_result['advice'],
                bullet_advice=analysis_result['bullet_advice']
            )
            
            # Update user's outfits field if authenticated
            if request.user.is_authenticated:
                outfit_data = {
                    'id': outfit_analysis.id,
                    'title': analysis_result['title'],
                    'description': analysis_result['description'],
                    'colors': analysis_result['colors'],
                    'timestamp': datetime.now().isoformat()
                }
                update_user_fields(request.user, outfit_data=outfit_data)
            
            # Return analysis result
            return Response(analysis_result, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Server error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TextQueryView(APIView):
    """
    API endpoint for text-based queries
    POST /api/ai/text-query/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            serializer = TextQuerySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            query = serializer.validated_data['query']
            session_id = serializer.validated_data.get('session_id', str(uuid4()))
            user_id = request.user.id if request.user.is_authenticated else None
            
            # Handle text query with AI
            response_text = handle_text_query_with_ai(query, session_id, user_id)
            
            # Save to session history
            save_session_history(session_id, query, response_text, user_id)
            
            # Update user's conversation field if authenticated
            if request.user.is_authenticated:
                conversation_data = {
                    'query': query,
                    'response': response_text,
                    'timestamp': datetime.now().isoformat()
                }
                update_user_fields(request.user, conversation_data=conversation_data)
            
            return Response({
                "response": response_text,
                "session_id": session_id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": "Server error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatView(APIView):
    """
    Combined API endpoint for chatbot queries (text, text+image, image only)
    POST /api/ai/chat/
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        try:
            # Parse form data
            query = request.data.get('query', '').strip()
            image_file = request.FILES.get('image')
            session_id = request.data.get('session_id', str(uuid4()))
            user_id = request.user.id if request.user.is_authenticated else None
            
            # Validate inputs
            if not query and not image_file:
                return Response({"error": "Must provide query or image"}, status=status.HTTP_400_BAD_REQUEST)
            
            if image_file and image_file.size > 5 * 1024 * 1024:
                return Response({"error": "Image size exceeds 5MB limit"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Case 1: Text only
            if query and not image_file:
                response_text = handle_text_query_with_ai(query, session_id, user_id)
                user_input = query
                
                # Save to session history
                save_session_history(session_id, user_input, response_text, user_id)
                
                # Update user conversation
                if request.user.is_authenticated:
                    conversation_data = {
                        'query': query,
                        'response': response_text,
                        'timestamp': datetime.now().isoformat()
                    }
                    update_user_fields(request.user, conversation_data=conversation_data)
            
            # Case 2: Text + Image
            elif query and image_file:
                analysis = analyze_outfit_with_ai(image_file, session_id, user_id)
                combined_query = f"Query: {query}\nBased on the outfit analysis: {json.dumps(analysis)}"
                response_text = handle_text_query_with_ai(combined_query, session_id, user_id)
                user_input = f"Image upload with query: {query}"
                
                # Save outfit analysis
                outfit_analysis = OutfitAnalysis.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    session_id=session_id,
                    image=image_file,
                    title=analysis['title'],
                    colors=analysis['colors'],
                    description=analysis['description'],
                    advice=analysis['advice'],
                    bullet_advice=analysis['bullet_advice']
                )
                
                # Save to session history
                save_session_history(session_id, user_input, response_text, user_id, image_file, analysis)
                
                # Update user fields
                if request.user.is_authenticated:
                    conversation_data = {
                        'query': query,
                        'response': response_text,
                        'image_analysis': analysis,
                        'timestamp': datetime.now().isoformat()
                    }
                    outfit_data = {
                        'id': outfit_analysis.id,
                        'title': analysis['title'],
                        'description': analysis['description'],
                        'colors': analysis['colors'],
                        'timestamp': datetime.now().isoformat()
                    }
                    update_user_fields(request.user, conversation_data, outfit_data)
            
            # Case 3: Image only
            else:  # image_file and not query
                analysis = analyze_outfit_with_ai(image_file, session_id, user_id)
                response_text = analysis['advice']
                user_input = "Image upload"
                
                # Save outfit analysis
                outfit_analysis = OutfitAnalysis.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    session_id=session_id,
                    image=image_file,
                    title=analysis['title'],
                    colors=analysis['colors'],
                    description=analysis['description'],
                    advice=analysis['advice'],
                    bullet_advice=analysis['bullet_advice']
                )
                
                # Save to session history
                save_session_history(session_id, user_input, response_text, user_id, image_file, analysis)
                
                # Update user fields
                if request.user.is_authenticated:
                    outfit_data = {
                        'id': outfit_analysis.id,
                        'title': analysis['title'],
                        'description': analysis['description'],
                        'colors': analysis['colors'],
                        'timestamp': datetime.now().isoformat()
                    }
                    update_user_fields(request.user, outfit_data=outfit_data)
            
            return Response({
                "response": response_text,
                "session_id": session_id
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Server error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserOutfitHistoryView(generics.ListAPIView):
    """
    Get user's outfit analysis history
    GET /api/ai/outfit-history/
    """
    serializer_class = OutfitAnalysisSerializer

    from rest_framework.pagination import PageNumberPagination
    class OutfitHistoryPagination(PageNumberPagination):
        page_size = 10
        page_size_query_param = 'page_size'
        max_page_size = 100

    pagination_class = OutfitHistoryPagination

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return OutfitAnalysis.objects.filter(user=self.request.user)
        return OutfitAnalysis.objects.none()

class UserConversationHistoryView(generics.ListAPIView):
    """
    Get user's conversation history
    GET /api/ai/conversation-history/
    """
    serializer_class = SessionHistorySerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return SessionHistory.objects.filter(user_id=str(self.request.user.id))
        return SessionHistory.objects.none()

class OutfitAnalysisDetailView(generics.RetrieveAPIView):
    """
    Get specific outfit analysis
    GET /api/ai/outfit-analysis/<id>/
    """
    serializer_class = OutfitAnalysisSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return OutfitAnalysis.objects.filter(user=self.request.user)
        return OutfitAnalysis.objects.none()
# from django.shortcuts import render

# # Create your views here.
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from .serializers import OutfitAnalysisRequestSerializer, OutfitAnalysisResponseSerializer, TextQueryRequestSerializer, SessionHistorySerializer
# from .utils import analyze_outfit, handle_text_query, save_to_json
# from .models import SessionHistory

# class OutfitAnalysisView(APIView):
#     def post(self, request):
#         serializer = OutfitAnalysisRequestSerializer(data=request.data)
#         if serializer.is_valid():
#             image = serializer.validated_data['image']
#             context = serializer.validated_data.get('context', '')
#             user_id = serializer.validated_data['user_id']
            
#             analysis = analyze_outfit(image, context, user_id)
#             if not analysis:
#                 return Response({"error": "Could not analyze the outfit. Please try another image."}, status=status.HTTP_400_BAD_REQUEST)
            
#             # Validate response
#             response_serializer = OutfitAnalysisResponseSerializer(data=analysis)
#             if not response_serializer.is_valid():
#                 return Response({"error": "Invalid analysis response format."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
#             # Save to session history with image and user_id
#             SessionHistory.objects.create(
#                 user_id=user_id,
#                 user_input=f"upload (image) with context: {context}" if context else "upload (image)",
#                 response=analysis['advice'],
#                 image=image
#             )
            
#             # Save analysis to JSON file
#             save_to_json(analysis)
            
#             return Response(response_serializer.data, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class TextQueryView(APIView):
#     def post(self, request):
#         serializer = TextQueryRequestSerializer(data=request.data)
#         if serializer.is_valid():
#             query = serializer.validated_data['query']
#             user_id = serializer.validated_data['user_id']
            
#             response_text = handle_text_query(query, user_id)
            
#             # Save to session history (no image for text queries)
#             SessionHistory.objects.create(
#                 user_id=user_id,
#                 user_input=query,
#                 response=response_text
#             )
            
#             return Response({"response": response_text}, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PromptViewSet(viewsets.ModelViewSet):
    serializer_class = PromptSerializer
    permission_classes = [AdminOrReadOnly]
    
    def list(self, request):
        prompt_obj = Prompt.initial_or_get_prompt()
        data = PromptSerializer(prompt_obj).data
        return Response(data, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        object = Prompt.objects.first()
        serializer = self.get_serializer(object, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        object = Prompt.objects.first()
        serializer = self.get_serializer(object, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=False, methods=['POST'], url_path='reset', permission_classes=[AdminOrReadOnly])
    def reset_prompt(self, request):
        """
        Reset the prompt to default values.
        """
        object = Prompt.objects.first()
        if not object:
           object = Prompt.objects.create(system_prompt="Default system prompt", image_prompt="Default image prompt")
        else:
            object.system_prompt = PHOTO_PROMPT
            object.image_prompt = SYSTEM_PROMPT
            object.save()
        return Response({"message": "Prompt reset to default values", 
                         "data": PromptSerializer(object).data
                         }, status=status.HTTP_200_OK)
        