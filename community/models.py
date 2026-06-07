from django.db import models
from django.conf import settings
import random
import string
from django.contrib.contenttypes.models import ContentType
User = settings.AUTH_USER_MODEL
# Create your models here.
class Community(models.Model):

    COMMUNITY_TYPE = (
        ('public', 'Public'),
        ('private', 'Private'),
    )

    name = models.CharField(max_length=200)
    description = models.TextField()

    interest = models.CharField(max_length=100)

    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    community_type = models.CharField(max_length=10, choices=COMMUNITY_TYPE)

    cover_image = models.ImageField(upload_to="community_cover/", blank=True, null=True)

    rules = models.TextField(blank=True)

    allow_post = models.BooleanField(default=True)
    allow_trip = models.BooleanField(default=True)

    max_members = models.IntegerField(blank=True, null=True)

    tags = models.CharField(max_length=200, blank=True)


    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    title = models.CharField(max_length=200) 
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="post_images/")

class PostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        unique_together = ['user', 'post']   # ✅ one like per user

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name="comments")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Trip(models.Model):

    VISIBILITY_CHOICES = (
        ('community', 'Community'),
        ('private', 'Private'),
    )

    JOIN_TYPE_CHOICES = (
        ('approval', 'Approval Required'),
        ('direct', 'Direct Join'),
    )

    community = models.ForeignKey(
        "Community",
        on_delete=models.CASCADE,
        related_name="trips",
        null=True,
        blank=True
    )

    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    # ✅ NEW
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='private'
    )

    # ✅ NEW
    join_type = models.CharField(
        max_length=20,
        choices=JOIN_TYPE_CHOICES,
        default='direct'
    )

    # ✅ NEW
    invite_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    title = models.CharField(max_length=200)
    description = models.TextField()

    duration_days = models.IntegerField()
    duration_nights = models.IntegerField()

    places_covered = models.CharField(max_length=300)

    budget = models.DecimalField(max_digits=10, decimal_places=2)

    trip_type = models.CharField(max_length=100)

    start_date = models.DateField()
    end_date = models.DateField()

    rules = models.TextField()

    max_members = models.IntegerField()

    cancellation_policy = models.TextField(blank=True, null=True)
    inclusions = models.TextField(blank=True, null=True)
    exclusions = models.TextField(blank=True, null=True)
    things_to_pack = models.TextField(blank=True, null=True)

    # ✅ NEW
    live_tracking_enabled = models.BooleanField(default=False)

    # ✅ NEW
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        if not self.invite_code:
            self.invite_code = ''.join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=8
                )
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class TripImage(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="trip_images/")
    
    def __str__(self):
        return f"Image for {self.trip.title}"

class TripItinerary(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="itineraries")

    day_number = models.IntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return f"{self.trip.title} - Day {self.day_number}"


class CommunityMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        related_name="members"   # ✅ ADD THIS
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)

class JoinRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)

    status = models.CharField(
        max_length=10,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)


from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
class Notification(models.Model):
    NOTIFICATION_TYPE = (
        # Community related
        ('join_request', 'Join Request'),
        ('request_approved', 'Request Approved'),
        ('trip_update', 'Trip Update'),
        ('post_like', 'Post Like'),
        ('comment', 'Comment'),
        ('poll_vote', 'Poll Vote'),
        ('booking', 'New Booking'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('trip_completed', 'Trip Completed'),
        
        # Buddy/Friend related
        ('buddy_request', 'Buddy Request'),
        ('buddy_request_accepted', 'Buddy Request Accepted'),
        ('buddy_request_rejected', 'Buddy Request Rejected'),
        
        # Social/Profile related
        ('profile_like', 'Profile Post Like'),
        ('profile_comment', 'Profile Post Comment'),
        ('follow', 'New Follower'),

        # Destination approvals
        ('destination_approved', 'Destination Approved'),
        ('destination_rejected', 'Destination Rejected'),

        # Place approvals
        ('place_approved', 'Place Approved'),
        ('place_rejected', 'Place Rejected'),
        ('message', 'Message'),

        ('complaint_created', 'Complaint Created'),
        ('complaint_response', 'Complaint Response'),
        ('complaint_resolved', 'Complaint Resolved'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_notifications') 
    
    # Existing foreign keys
    community = models.ForeignKey('Community', on_delete=models.CASCADE, null=True, blank=True)
    request = models.ForeignKey('JoinRequest', on_delete=models.CASCADE, null=True, blank=True)
    profile_post = models.ForeignKey(
        'travellers.ProfilePost',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    # New foreign keys for buddy system
    buddy_request = models.ForeignKey(
        'travellers.BuddyRequest',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    # Generic fields for any other type of content
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    message = models.TextField()
    notification_type = models.CharField(max_length=25, choices=NOTIFICATION_TYPE)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"


    @classmethod
    def create_post_like_notification(cls, post, liked_by_user):
        """Create notification for post like"""
        if post.user != liked_by_user:  # Don't notify for self-like
            return cls.objects.create(
                user=post.user,
                sender=liked_by_user,
                profile_post=post,
                notification_type='profile_like',
                message=f"{liked_by_user.get_full_name() or liked_by_user.username} liked your post",
            )
        return None

    @classmethod
    def create_post_comment_notification(cls, post, comment_by_user, comment_text):
        """Create notification for post comment"""
        if post.user != comment_by_user:  # Don't notify for self-comment
            return cls.objects.create(
                user=post.user,
                sender=comment_by_user,
                profile_post=post,
                notification_type='profile_comment',
                message=f"{comment_by_user.get_full_name() or comment_by_user.username} commented: '{comment_text[:50]}'",
            )
        return None

    @classmethod
    def create_follow_notification(cls, follower, following_user):
        """Create notification for new follower"""
        if follower != following_user:  # Don't notify for self-follow
            return cls.objects.create(
                user=following_user,
                sender=follower,
                notification_type='follow',
                message=f"{follower.get_full_name() or follower.username} started following you",
            )
        return None
    
    @classmethod
    def create_buddy_request_notification(cls, from_user, to_user, buddy_request):
        """Create notification for buddy request"""
        return cls.objects.create(
            user=to_user,
            sender=from_user,
            buddy_request=buddy_request,
            notification_type='buddy_request',
            message=f"{from_user.get_full_name() or from_user.username} sent you a buddy request",
        )

    @classmethod
    def create_buddy_accepted_notification(cls, from_user, to_user, buddy_request):
        """Create notification for accepted buddy request"""
        return cls.objects.create(
            user=to_user,
            sender=from_user,
            buddy_request=buddy_request,
            notification_type='buddy_request_accepted',
            message=f"{from_user.get_full_name() or from_user.username} accepted your buddy request",
        )

    @classmethod
    def create_buddy_rejected_notification(cls, from_user, to_user, buddy_request):
        """Create notification for rejected buddy request (optional)"""
        return cls.objects.create(
            user=to_user,
            sender=from_user,
            buddy_request=buddy_request,
            notification_type='buddy_request_rejected',
            message=f"{from_user.get_full_name() or from_user.username} declined your buddy request",
        )
    
    @classmethod
    def create_destination_approved_notification(cls, destination):
        return cls.objects.create(
            user=destination.created_by,
            notification_type='destination_approved',
            message=f'🎉 Your destination "{destination.name}" has been approved and is now live.'
        )


    @classmethod
    def create_destination_rejected_notification(cls, destination):
        return cls.objects.create(
            user=destination.created_by,
            notification_type='destination_rejected',
            message=f'❌ Your destination "{destination.name}" was rejected by the admin.'
        )


    @classmethod
    def create_place_approved_notification(cls, place):
        return cls.objects.create(
            user=place.created_by,
            notification_type='place_approved',
            message=f'🎉 Your place "{place.name}" has been approved and is now visible to travelers.'
        )


    @classmethod
    def create_place_rejected_notification(cls, place):
        return cls.objects.create(
            user=place.created_by,
            notification_type='place_rejected',
            message=f'❌ Your place "{place.name}" was rejected by the admin.'
        )

    @classmethod
    def create_complaint_created_notification(
        cls,
        complaint,
        admin_user
    ):
        return cls.objects.create(
            user=admin_user,
            sender=complaint.user,
            notification_type='complaint_created',
            message=f"{complaint.user.username} submitted a complaint: {complaint.title}"
        )


    @classmethod
    def create_complaint_response_notification(
        cls,
        complaint,
        admin_user
    ):
        return cls.objects.create(
            user=complaint.user,
            sender=admin_user,

            content_type=ContentType.objects.get_for_model(
                complaint
            ),
            object_id=complaint.id,

            notification_type='complaint_response',

            message=f"Your complaint '{complaint.title}' has received a response."
        )


    @classmethod
    def create_complaint_resolved_notification(
        cls,
        complaint,
        admin_user
    ):
        return cls.objects.create(
            user=complaint.user,
            sender=admin_user,
            notification_type='complaint_resolved',
            message=f"Your complaint '{complaint.title}' has been marked as resolved."
        )

class Poll(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    question = models.CharField(max_length=255)
    image = models.ImageField(upload_to='polls/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    option_text = models.CharField(max_length=200)
    image = models.ImageField(upload_to='poll_options/', blank=True, null=True)

class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['poll', 'user']  # one vote per user



class TripParticipant(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    ROLE_CHOICES = [
        ("member", "Member"),
        ("coordinator", "Coordinator"),
    ]

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="participants"
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending"
    )

    # ✅ NEW
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="member"
    )

    # ✅ NEW
    is_location_sharing = models.BooleanField(default=False)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trip', 'user')


class ChatRoom(models.Model):
    CHAT_TYPE = (
        ('dm', 'Direct Message'),
        ('group', 'Group Chat'),
    )

    type = models.CharField(max_length=10, choices=CHAT_TYPE)
    name = models.CharField(max_length=255, blank=True)

    # ✅ ONE room per trip (CRITICAL FIX)
    trip = models.OneToOneField(
        Trip,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    participants = models.ManyToManyField(User,related_name="chat_rooms")
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)  # Add this field
    read_at = models.DateTimeField(null=True, blank=True)  # Optional: track when it was read

    def __str__(self):
        return f"{self.sender.username}: {self.text[:50]}"
    
    class Meta:
        ordering = ['created_at']


class LiveLocation(models.Model):

    participant = models.OneToOneField(
        TripParticipant,
        on_delete=models.CASCADE,
        related_name="location"
    )

    latitude = models.FloatField()
    longitude = models.FloatField()

    accuracy = models.FloatField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.participant.user.username} Location"


