from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
from groq import Groq
from django.conf import settings
from .models import ChatSession, ChatMessage

@login_required
def chatbot_page(request):
    """Main chatbot interface"""
    # Get or create active chat session
    session, created = ChatSession.objects.get_or_create(
        user=request.user,
        is_active=True,
        defaults={'is_active': True}
    )
    
    # If there are multiple active sessions, get the most recent one
    if not created:
        active_sessions = ChatSession.objects.filter(
            user=request.user, 
            is_active=True
        ).order_by('-updated_at')
        if active_sessions.count() > 1:
            # Deactivate older sessions
            active_sessions.exclude(id=session.id).update(is_active=False)
        session = active_sessions.first()
    
    # Get messages for this session
    messages = session.messages.all()
    
    context = {
        'session': session,
        'messages': messages,
    }
    return render(request, 'chatbot/chatbot.html', context)

@login_required
@require_http_methods(["POST"])
def send_message(request):
    """Handle sending messages and getting AI responses"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        print(f"Received message: {user_message}")  # Debug log
        print(f"Session ID: {session_id}")  # Debug log
        
        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Get or create session
        if session_id:
            session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        else:
            session, created = ChatSession.objects.get_or_create(
                user=request.user,
                is_active=True
            )
        
        # Save user message
        user_msg = ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_message
        )
        
        # Prepare conversation history for Groq
        messages = []
        
        # System prompt
        system_prompt = """
You are Wayzo AI, a smart travel assistant for the Wayzo Travel Management Platform.

Wayzo connects travellers, restaurants, and travel agencies in a single ecosystem.

Platform Features:

1. Destinations
- Users can explore destinations.
- Each destination contains multiple tourist places and attractions.
- Users can view destination details, photos, and travel information.

2. Travel Packages
- Travel agencies create and manage travel packages.
- Travellers can browse, compare, and book packages.
- Packages may include sightseeing, accommodation, transportation, and activities.

3. Restaurant Reservations
- Restaurants can list rooms and dining tables.
- Travellers can book rooms and reserve tables.
- Restaurant owners manage availability and bookings.

4. Community
- Travellers can create posts.
- Users can like, comment, and interact with community content.
- Users can follow other travellers.

5. User Types
- Traveller
- Restaurant Owner
- Travel Agency

6. Bookings
- Travellers can book:
    - Travel Packages
    - Restaurant Rooms
    - Restaurant Tables

7. Support
- Users can contact support through the platform.

Guidelines:
- Be friendly and professional.
- Keep answers concise and practical.
- Help users navigate platform features.
- Suggest relevant platform features when useful.
- Do not invent information that does not exist.
- If unsure, advise the user to contact support.

Always answer as a travel platform assistant.
"""
        
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        history_messages = session.messages.order_by('-created_at')[:20]
        for msg in reversed(history_messages):
            if msg.role == 'user':
                messages.append({"role": "user", "content": msg.content})
            elif msg.role == 'assistant':
                messages.append({"role": "assistant", "content": msg.content})
        
        # Check if Groq API key is configured
        if not hasattr(settings, 'GROQ_API_KEY') or not settings.GROQ_API_KEY:
            print("GROQ_API_KEY not configured in settings")
            # Fallback response
            ai_response = """
I'm currently unable to access the AI service.

Meanwhile, you can:

• Explore destinations and tourist places
• Browse travel packages from agencies
• Book restaurant rooms and tables
• Participate in the community
• Manage your bookings

Please try again in a few moments.
"""
        else:
            try:
                # Initialize Groq client
                client = Groq(api_key=settings.GROQ_API_KEY)
                
                # Use a reliable model
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",  # Fast and reliable
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500,
                    top_p=1,
                    stream=False,
                    timeout=30
                )
                ai_response = completion.choices[0].message.content
                print("Successfully got response from Groq")  # Debug log
                
            except Exception as e:
                print(f"Groq API error: {str(e)}")  # Debug log
                # Fallback response
                ai_response = """
I'm currently unable to access the AI service.

Meanwhile, you can:

• Explore destinations and tourist places
• Browse travel packages from agencies
• Book restaurant rooms and tables
• Participate in the community
• Manage your bookings

Please try again in a few moments.
"""
        
        # Save AI response
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=ai_response
        )
        
        # Update session timestamp
        session.save()
        
        return JsonResponse({
            'success': True,
            'user_message': {
                'id': user_msg.id,
                'content': user_msg.content,
                'created_at': user_msg.created_at.isoformat(),
                'role': 'user'
            },
            'assistant_message': {
                'id': assistant_msg.id,
                'content': assistant_msg.content,
                'created_at': assistant_msg.created_at.isoformat(),
                'role': 'assistant'
            },
            'session_id': session.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Unexpected error in send_message: {str(e)}")  # Debug log
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

@login_required
@require_http_methods(["GET"])
def get_chat_history(request, session_id=None):
    """Get chat history for a session"""
    try:
        print(f"Getting history for session: {session_id}")  # Debug log
        
        if session_id:
            session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        else:
            session = ChatSession.objects.filter(user=request.user, is_active=True).first()
        
        if not session:
            return JsonResponse({'messages': [], 'session_id': None})
        
        messages = list(session.messages.all().values('id', 'role', 'content', 'created_at'))
        
        return JsonResponse({
            'messages': messages,
            'session_id': session.id
        })
    except Exception as e:
        print(f"Error in get_chat_history: {str(e)}")  # Debug log
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def clear_chat(request):
    """Clear current chat session and start new one"""
    try:
        print(f"Clearing chat for user: {request.user.username}")  # Debug log
        
        # Deactivate current sessions
        ChatSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
        
        # Create new session
        new_session = ChatSession.objects.create(user=request.user, is_active=True)
        
        return JsonResponse({
            'success': True,
            'session_id': new_session.id
        })
    except Exception as e:
        print(f"Error in clear_chat: {str(e)}")  # Debug log
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["GET"])
def get_sessions(request):
    """Get user's chat sessions"""
    try:
        print(f"Getting sessions for user: {request.user.username}")  # Debug log
        
        sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
        sessions_data = []
        
        for session in sessions:
            last_message = session.messages.filter(role='user').last()
            sessions_data.append({
                'id': session.id,
                'title': last_message.content[:50] if last_message else 'New Chat',
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'is_active': session.is_active
            })
        
        print(f"Found {len(sessions_data)} sessions")  # Debug log
        return JsonResponse({'sessions': sessions_data})
    except Exception as e:
        print(f"Error in get_sessions: {str(e)}")  # Debug log
        return JsonResponse({'error': str(e)}, status=500)