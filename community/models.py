from django.db import models
from django.conf import settings

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

    def __str__(self):
        return self.name

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    title = models.CharField(max_length=200) 
    content = models.TextField()

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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Trip(models.Model):

    community = models.ForeignKey("Community", on_delete=models.CASCADE, related_name="trips")
    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)
    description = models.TextField()

    duration_days = models.IntegerField()
    duration_nights = models.IntegerField()

    places_covered = models.CharField(max_length=300)
    budget = models.DecimalField(max_digits=10, decimal_places=2)

    trip_type = models.CharField(max_length=100)  # trekking, biking
    start_date = models.DateField()
    end_date = models.DateField()
    rules = models.TextField()
    max_members = models.IntegerField()
    cancellation_policy = models.TextField(blank=True, null=True)
    inclusions = models.TextField(blank=True, null=True)
    exclusions = models.TextField(blank=True, null=True)
    things_to_pack = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class TripImage(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="trip_images/")

class TripItinerary(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="itineraries")

    day_number = models.IntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return f"{self.trip.title} - Day {self.day_number}"

class TripParticipant(models.Model):

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    joined_at = models.DateTimeField(auto_now_add=True)


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

class Notification(models.Model):
    NOTIFICATION_TYPE = (
    ('join_request', 'Join Request'),
    ('request_approved', 'Request Approved'),
    ('trip_update', 'Trip Update'),
    ('post_like', 'Post Like'),
    ('comment', 'Comment'),
    ('poll_vote', 'Poll Vote'),
    ('trip_update', 'Trip Update'),
    ('booking', 'New Booking'),
    ('booking_cancelled', 'Booking Cancelled'),
    ('trip_completed', 'Trip Completed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True, blank=True)
    request = models.ForeignKey(JoinRequest, on_delete=models.CASCADE, null=True, blank=True)
    profile_post = models.ForeignKey(
        'travellers.ProfilePost',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


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

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    joined_at = models.DateTimeField(auto_now_add=True)


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

    participants = models.ManyToManyField(User)
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


