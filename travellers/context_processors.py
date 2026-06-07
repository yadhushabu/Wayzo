from .models import TravellerProfile

def user_profile_context(request):
    if request.user.is_authenticated:
        try:
            profile = TravellerProfile.objects.get(user=request.user)
            return {'profile': profile}
        except TravellerProfile.DoesNotExist:
            return {'profile': None}
    return {'profile': None}

from community.models import Message, ChatRoom
from travellers.models import BuddyRequest

def unread_messages_count(request):
    """Context processor to add unread messages count to all templates"""
    unread_count = 0
    
    if request.user.is_authenticated:
        # Get all rooms where user is a participant
        rooms = ChatRoom.objects.filter(participants=request.user)
        
        # Sum up unread messages across all rooms
        for room in rooms:
            unread_count += Message.objects.filter(
                room=room,
                is_read=False
            ).exclude(sender=request.user).count()
    
    return {
        'unread_messages_count': unread_count
    }


def buddy_pending_count(request):
    """Context processor to add pending buddy requests count to all templates"""
    pending_count = 0
    
    if request.user.is_authenticated:
        pending_count = BuddyRequest.objects.filter(
            to_user=request.user,
            status='pending'
        ).count()
    
    return {
        'buddy_pending_count': pending_count
    }