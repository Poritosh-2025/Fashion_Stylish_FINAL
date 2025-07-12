import os
import base64
import re
import json
from PIL import Image
from io import BytesIO
from openai import OpenAI
from django.conf import settings
from .models import SessionHistory

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Define prompts
# PHOTO_PROMPT = """Analyze the outfit in the provided image and respond with a compact JSON object:
# {"title": "Short creative title based on the outfit description (maximum 3 words)", 
#  "colors": ["color1", "color2", ...], 
#  "description": "Two-sentence description of the outfit.",
#  "advice": "Suggestions for improving the outfit tailored to a versatile, casual setting.",
#  "bullet_advice": ["First tip", "Second tip", "Third tip"]}
# - bullet_advice must contain up to 3 bullet points that summarize or rephrase parts of the advice field.
# - Do NOT add new suggestions in bullet_advice not present in the advice field.
# - 
# - Keep bullet points friendly, clear, and actionable.
# - Ensure the description is exactly two sentences.
# - Assume a versatile, casual setting for the advice.
# - Return only the JSON object with minimal whitespace and no newlines, markdown, or additional text."""

# SYSTEM_PROMPT = """You are Stailas, an AI fashion stylist designed to help users look and feel their best.
# - Use a friendly, upbeat, encouraging tone, like a trusted style-savvy friend.
# - Provide personalized, confidence-boosting advice, assuming a versatile, casual setting unless specified.
# - Avoid criticism; suggest positive alternatives (e.g., 'That's bold! To make it pop, try...').
# - Be concise (1-3 sentences) unless more detail is needed.
# - Use emojis (e.g., ✨, 👗) sparingly to keep responses sophisticated.
# - For image analysis, follow the provided photo prompt strictly and return only the JSON object.
# - For text queries, provide relevant fashion advice based on the input and conversation history.
# - Use conversation history to maintain context and relevance."""
PHOTO_PROMPT = """Analyze the outfit in the provided image and respond with a compact JSON object:
{"title": "Short creative title based on the outfit description (maximum 3 words)",
 "colors": ["color1", "color2", ...],
 "description": "Two-sentence description of the outfit.",
 "advice": "Suggestions for improving the outfit tailored to the specified occasion.",
 "bullet_advice": [ Make upto 3 bullet points from the advice field " First tip", " Second tip" ....]}
- bullet_advice must contain only bullet points that summarize or rephrase parts of the advice field.
- Do NOT add any new suggestions in bullet_advice that are not already present in the advice field.
- bullet_advice must NOT include clarification questions or follow-up queries.
- In the color generate the hash code for that color and take upto 3 prominent colors.
- If a clarification is needed, include it in the advice field only, not in bullet_advice.
- Keep bullet points friendly, clear, and actionable.
- Ensure the description is exactly two sentences.
- Assume a versatile, casual setting for the advice.
- Return only the JSON object with minimal whitespace and no newlines, markdown, or additional text."""
 
SYSTEM_PROMPT = """You are Stailas, an AI fashion stylist designed to help users look and feel their best.
- Use a friendly, upbeat, encouraging tone, like a trusted style-savvy friend.
- Provide personalized, confidence-boosting advice, assuming a versatile, casual setting unless specified.
- Avoid criticism; suggest positive alternatives (e.g., 'That’s bold! To make it pop, try...').
- Be concise (1-3 sentences) unless more detail is needed.
- Use emojis (e.g., ✨, 👗) sparingly to keep responses sophisticated.
- While answering don't take the name of the dress.
- For image analysis, follow the provided photo prompt strictly and return only the JSON object.
- For text queries, provide relevant fashion advice based on the input and conversation history.
- Use conversation history to maintain context and relevance."""
def encode_image(image_file):
    """Encode image to base64 for OpenAI API"""
    try:
        # Read and validate image
        img = Image.open(image_file)
        img.verify()  # Verify image integrity
        img = Image.open(image_file)  # Reopen after verify
        img_format = img.format.lower()
        
        if img_format not in ['jpeg', 'jpg', 'png']:
            raise ValueError("Unsupported image format")
        
        # Convert to JPEG if PNG to ensure compatibility
        if img_format == 'png':
            buffer = BytesIO()
            img.convert('RGB').save(buffer, format="JPEG", quality=85)
            img_data = buffer.getvalue()
        else:
            buffer = BytesIO()
            img.save(buffer, format=img_format, quality=85)
            img_data = buffer.getvalue()
        
        return base64.b64encode(img_data).decode('utf-8')
    except Exception as e:
        raise ValueError(f"Invalid image: {str(e)}")

def get_session_history(session_id, user_id=None):
    """Get conversation history for context"""
    try:
        query = SessionHistory.objects.filter(session_id=session_id).order_by('timestamp')
        if user_id:
            query = query.filter(user_id=str(user_id))
        
        history = query[:10]  # Last 10 interactions
        
        if history.exists():
            history_context = "\nConversation history:\n" + "\n".join([
                f"User: {entry.user_input}\nStailas: {entry.response}" 
                for entry in history
            ])
            return history_context
        return ""
    except Exception:
        return ""

def analyze_outfit_with_ai(image_file, session_id=None, user_id=None):
    """Analyze outfit using OpenAI GPT-4o"""
    try:
        base64_image = encode_image(image_file)
        
        # Include session history if provided
        history_context = get_session_history(session_id, user_id)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + history_context},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PHOTO_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=300
        )
        
        # Extract JSON from response
        response_text = response.choices[0].message.content.strip()
        json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
        
        if not json_match:
            raise ValueError("No valid JSON found in response")
        
        json_str = json_match.group(0)
        result = json.loads(json_str)
        
        # Validate required keys
        required_keys = ["title", "colors", "description", "advice", "bullet_advice"]
        if not isinstance(result, dict) or not all(key in result for key in required_keys):
            raise ValueError("Invalid JSON structure")
        
        return result
    except Exception as e:
        raise ValueError(f"Analysis failed: {str(e)}")

def handle_text_query_with_ai(query, session_id=None, user_id=None):
    """Handle text-based queries using OpenAI"""
    try:
        # Include session history if provided
        history_context = get_session_history(session_id, user_id)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + history_context},
                {"role": "user", "content": query}
            ],
            max_tokens=150
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Sorry, I couldn't process that. Try another question! 😊"

def save_session_history(session_id, user_input, response, user_id=None, image=None, analysis_data=None):
    """Save conversation to session history"""
    try:
        SessionHistory.objects.create(
            session_id=session_id,
            user_id=str(user_id) if user_id else None,
            user_input=user_input,
            response=response,
            image=image,
            analysis_data=analysis_data
        )
        
        # Keep only last 10 sessions per user/session
        history = SessionHistory.objects.filter(session_id=session_id).order_by('-timestamp')
        if user_id:
            history = history.filter(user_id=str(user_id))
        
        if history.count() > 10:
            old_entries = history[10:]
            for entry in old_entries:
                entry.delete()
                
    except Exception as e:
        print(f"Error saving session history: {e}")

def update_user_fields(user, conversation_data=None, outfit_data=None):
    """Update user's conversation and outfits fields"""
    try:
        if conversation_data:
            existing_conversations = []
            if user.conversation:
                try:
                    existing_conversations = json.loads(user.conversation)
                except (json.JSONDecodeError, TypeError):
                    existing_conversations = []
            
            existing_conversations.append(conversation_data)
            # Keep last 20 conversations
            user.conversation = json.dumps(existing_conversations[-20:])
        
        if outfit_data:
            existing_outfits = []
            if user.outfits:
                try:
                    existing_outfits = json.loads(user.outfits)
                except (json.JSONDecodeError, TypeError):
                    existing_outfits = []
            
            existing_outfits.append(outfit_data)
            # Keep last 20 outfits
            user.outfits = json.dumps(existing_outfits[-20:])
        
        user.save()
    except Exception as e:
        print(f"Error updating user fields: {e}")

# import os
# import json
# import base64
# import re
# import ast
# from datetime import datetime
# from PIL import Image
# from openai import OpenAI
# from django.conf import settings
# from .models import SessionHistory

# # Load environment variables
# from dotenv import load_dotenv
# load_dotenv()

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# # Define prompts
# photo_prompt = """Analyze the outfit in the provided image and respond with a compact JSON object:
# {"title": "Short creative title based on the outfit description (maximum 3 words)", "colors": ["color1", "color2", ...], "description": "Two-sentence description of the outfit.",
#  "advice": "Suggestions for improving the outfit tailored to the specified occasion."}
# - Focus on the clothing, not the background.
# - Generate a short, catchy, and relevant title based on the outfit description (e.g., 'Chic Monochrome Layers', 'Sunset Boho Vibes').
# - Ensure the description is exactly two sentences.
# - Tailor advice to the occasion provided in the user's context (e.g., wedding, casual, formal) or assume a versatile, casual setting if no occasion is specified.
# - If the user's context lacks a clear occasion, include a follow-up question in the advice field to clarify the occasion (e.g., 'Consider adding a clutch for a formal event; what occasion is this outfit for?').
# - Consider fit, color harmony, and appropriateness for the occasion and any additional context (e.g., body shape, preferences).
# - Return only the JSON object with minimal whitespace and no newlines, markdown, or additional text.
# - The advice field should contain styling suggestions relevant to the occasion."""

# system_prompt = """You are Stailas, an AI fashion stylist designed to help users look and feel their best, no matter their style, shape, or budget.
# - Use a friendly, upbeat, encouraging tone, like a trusted style-savvy friend.
# - Provide personalized, confidence-boosting advice, prioritizing the occasion and considering body shape, skin tone, lifestyle, budget, or preferences if mentioned.
# - Avoid criticism; suggest positive alternatives (e.g., 'That's bold! To make it pop, try...').
# - Be concise (1-3 sentences) on social platforms, detailed in an app setting.
# - Occasionally use emojis (e.g., ✨, 👗) on social platforms, but keep it sophisticated.
# - If context is missing, assume a versatile, casual setting and make reasonable suggestions.
# - Include a follow-up question only when clarification is needed (e.g., to confirm the occasion or preferences).
# - For outfit suggestions, explain why they work and how to style them, ensuring alignment with the occasion.
# - Use the provided conversation history to maintain context and make responses relevant to previous interactions.
# Also consider this if someone sends a photo: {photo_prompt}.""".format(photo_prompt=photo_prompt)

# def encode_image(image_file):
#     return base64.b64encode(image_file.read()).decode('utf-8')

# def analyze_outfit(image_file, user_text, user_id):
#     try:
#         # Verify image
#         img = Image.open(image_file)
#         img.verify()
#         image_file.seek(0)  # Reset file pointer after verification
#         base64_image = encode_image(image_file)
        
#         # Get user history
#         user_history = SessionHistory.objects.filter(user_id=user_id).order_by('timestamp')
#         history_context = "\nConversation history:\n" + "\n".join(
#             [f"User: {entry.user_input}\nStailas: {entry.response}" for entry in user_history]
#         ) if user_history else ""
        
#         # Combine photo prompt with user text
#         user_content = [
#             {"type": "text", "text": photo_prompt + (f"\nAdditional context: {user_text}" if user_text else "")},
#             {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
#         ]
        
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": system_prompt + history_context},
#                 {"role": "user", "content": user_content}
#             ],
#             max_tokens=300
#         )
        
#         # Extract JSON
#         response_text = response.choices[0].message.content.strip()
#         json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
#         if not json_match:
#             return None
        
#         json_str = json_match.group(0)
        
#         try:
#             result = json.loads(json_str)
#         except json.JSONDecodeError:
#             try:
#                 result = ast.literal_eval(json_str)
#             except (ValueError, SyntaxError):
#                 return None
        
#         if isinstance(result, dict) and all(key in result for key in ["title", "colors", "description", "advice"]):
#             return result
#         return None
#     except Exception:
#         return None

# def handle_text_query(query, user_id):
#     try:
#         user_history = SessionHistory.objects.filter(user_id=user_id).order_by('timestamp')
#         history_context = "\nConversation history:\n" + "\n".join(
#             [f"User: {entry.user_input}\nStailas: {entry.response}" for entry in user_history]
#         ) if user_history else ""
        
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": system_prompt + history_context},
#                 {"role": "user", "content": query}
#             ],
#             max_tokens=150
#         )
#         return response.choices[0].message.content
#     except Exception:
#         return "Sorry, I couldn't process that. Try another question! 😊"

# def save_to_json(analysis):
#     if not analysis:
#         return
    
#     output_dir = os.path.join(settings.MEDIA_ROOT, 'output')
#     os.makedirs(output_dir, exist_ok=True)
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
#     filename = f"{output_dir}/output_{timestamp}.json"
    
#     with open(filename, 'w') as f:
#         json.dump(analysis, f, indent=4)