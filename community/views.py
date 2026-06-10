import json
from random import randint

from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db.models import Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from admin_app.utils import create_audit_log

from .models import ChatRoom, Community, CommunityMember, JoinRequest, LiveLocation, Notification, Poll, PollOption, PollVote, Post, PostImage, PostLike, Trip, TripImage, TripItinerary, TripParticipant, Comment, Message
from .forms import CommunityForm, PostForm, PostImageForm, PostImageFormSet, TripForm, TripImageFormSet, TripItineraryFormSet

from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def community_home(request):
    """Community home page - Shows user's communities and activity"""

    # Communities created by current user
    created_communities = (
        Community.objects.filter(creator=request.user)
        .annotate(members_count=Count('members'))
        .order_by('-created_at')
    )

    # Communities joined by current user
    joined_communities = (
        Community.objects.filter(members__user=request.user)
        .exclude(creator=request.user)
        .annotate(members_count=Count('members'))
        .distinct()
        .order_by('-created_at')
    )

    # Recent notifications
    notifications = (
        Notification.objects.filter(user=request.user)
        .select_related('sender', 'community', 'buddy_request', 'profile_post')
        .order_by('-created_at')[:10]
    )

    # Unread notification count
    unread_notifications_count = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).count()

    # Hero Image - Get random community with cover image
    hero_image = '/static/images/community-hero.jpg'
    
    communities_with_cover = list(
        Community.objects.exclude(cover_image__isnull=True)
        .exclude(cover_image='')
        .values_list('id', 'cover_image')
    )
    
    if communities_with_cover:
        import random
        random_community = random.choice(communities_with_cover)
        hero_image = random_community[1]

    # Statistics
    total_communities = Community.objects.count()
    
    # Count total members
    total_members = 0
    for community in Community.objects.all():
        total_members += community.members.count()
    
    total_posts = Post.objects.count()

    private_trips = Trip.objects.filter(
        visibility="private"
    ).filter(
        Q(creator=request.user) |           # trips I created
        Q(participants__user=request.user)  # trips I joined
    ).distinct().select_related('creator').prefetch_related('participants', 'images').order_by('-created_at')[:6]

    context = {
        'created_communities': created_communities,
        'joined_communities': joined_communities,
        'notifications': notifications,
        'hero_image': hero_image,
        'total_communities': total_communities,
        'total_members': total_members,
        'total_posts': total_posts,
        'unread_notifications_count': unread_notifications_count,
        'private_trips': private_trips,
    }

    return render(request, "community/community_home.html", context)


@login_required
def create_community(request):
    """Create a new community"""
    
    if request.method == "POST":
        form = CommunityForm(request.POST, request.FILES)
        if form.is_valid():
            community = form.save(commit=False)
            community.creator = request.user
            
            # Get community type from form
            community_type = request.POST.get('community_type', 'public')
            community.community_type = community_type
            
            community.save()

            create_audit_log(
                user=request.user,
                action='community_created',
                description=f'Created community: {community.name}'
            )
            
            # Creator becomes member + admin
            CommunityMember.objects.create(
                user=request.user,
                community=community,
                is_admin=True
            )
            
            messages.success(request, f'✨ Community "{community.name}" created successfully!')
            return redirect("community:community_detail", pk=community.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CommunityForm()
    
    return render(request, "community/create_community.html", {"form": form})

@login_required
def leave_community(request, community_id):
    """Allow a user to leave a community"""
    community = get_object_or_404(Community, id=community_id)
    
    # Check if user is a member
    membership = CommunityMember.objects.filter(
        user=request.user, 
        community=community
    ).first()
    
    if membership:
        # Prevent creator from leaving (they can delete instead)
        if request.user == community.creator:
            messages.error(request, "As the creator, you cannot leave. You can delete the community instead.")
            return redirect('community:community_detail', pk=community.id)
        
        # Remove membership
        membership.delete()
        messages.success(request, f"You have left {community.name}")
        
        # Notify creator
        Notification.objects.create(
            user=community.creator,
            community=community,
            message=f"{request.user.username} left {community.name}",
            notification_type="community_update"
        )
    else:
        messages.warning(request, "You are not a member of this community")
    
    return redirect('community:community_list')


def community_list(request):
    """Browse all communities with search, filter, and sorting"""
    
    # Base queryset
    communities = Community.objects.all().annotate(
        members_count=Count('members')
    ).order_by('-created_at')
    
    # Exclude communities user has already joined or created
    if request.user.is_authenticated:
        joined_ids = CommunityMember.objects.filter(
            user=request.user
        ).values_list("community_id", flat=True)
        
        communities = communities.exclude(id__in=joined_ids)
        communities = communities.exclude(creator=request.user)
    
    # Search functionality
    search_query = request.GET.get('q', '').strip()
    if search_query:
        communities = communities.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(interest__icontains=search_query)
        )
    
    # Filter by community type (public/private)
    community_type = request.GET.get('type', '')
    if community_type and community_type != 'all':
        if community_type == 'public':
            communities = communities.filter(community_type='public')
        elif community_type == 'private':
            communities = communities.filter(community_type='private')
    
    # Filter by interest/category
    interest_filter = request.GET.get('interest', '')
    valid_interests = ['adventure', 'beach', 'cultural', 'food', 'backpacking', 'luxury', 'pilgrimage']
    if interest_filter and interest_filter in valid_interests:
        communities = communities.filter(interest__iexact=interest_filter)
    
    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'members':
        communities = communities.order_by('-members_count')
    elif sort_by == 'name':
        communities = communities.order_by('name')
    elif sort_by == 'oldest':
        communities = communities.order_by('created_at')
    else:  # newest
        communities = communities.order_by('-created_at')
    
    # Get joined and requested community IDs for the current user
    joined_community_ids = []
    requested_community_ids = []
    
    if request.user.is_authenticated:
        joined_community_ids = list(CommunityMember.objects.filter(
            user=request.user
        ).values_list('community_id', flat=True))
        
        requested_community_ids = list(JoinRequest.objects.filter(
            user=request.user,
            status='pending'
        ).values_list('community_id', flat=True))
    
    # Pagination
    paginator = Paginator(communities, 12)  # Show 12 communities per page
    page = request.GET.get('page', 1)
    
    try:
        communities_page = paginator.page(page)
    except PageNotAnInteger:
        communities_page = paginator.page(1)
    except EmptyPage:
        communities_page = paginator.page(paginator.num_pages)
    
    context = {
        'communities': communities_page,
        'search_query': search_query,
        'community_type': community_type,
        'interest_filter': interest_filter,
        'sort_by': sort_by,
        'joined_community_ids': joined_community_ids,
        'requested_community_ids': requested_community_ids,
        'total_count': paginator.count,
        'valid_interests': valid_interests,
    }
    
    return render(request, "community/community_list.html", context)

@login_required
def join_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    # already joined
    if CommunityMember.objects.filter(user=request.user, community=community).exists():
        return redirect("community:community_detail", pk=community.id)

    # PUBLIC → direct join
    if community.community_type == "public":
        CommunityMember.objects.create(
            user=request.user,
            community=community
        )

        # Notify USER
        Notification.objects.create(
            user=request.user,
            community=community,
            message=f"You joined {community.name}",
            notification_type="request_approved"
        )

        # Notify CREATOR
        if request.user != community.creator:
            Notification.objects.create(
                user=community.creator,
                community=community,
                message=f"{request.user.username} joined your community {community.name}",
                notification_type="request_approved"
            )

    # PRIVATE → send request
    else:
        join_request, created = JoinRequest.objects.get_or_create(
            user=request.user,
            community=community
        )

        if created:
            Notification.objects.create(
                user=community.creator,
                community=community,
                request=join_request,
                message=f"{request.user.username} requested to join {community.name}",
                notification_type="join_request"
            )
            messages.info(request, f"Join request sent to {community.name}")
        else:
            messages.info(request, "Your join request is already pending")

    return redirect("community:community_list")


@login_required
def notifications_view(request):

    notifications = (
        Notification.objects
        .filter(user=request.user)
        .select_related(
            'sender',
            'buddy_request',
            'profile_post',
            'community',
            'content_type'
        )
        .order_by('-created_at')
    )

    unread_count = notifications.filter(
        is_read=False
    ).count()

    context = {
        "notifications": notifications,
        "unread_count": unread_count,
    }

    # ======================================
    # ADMIN
    # ======================================

    if (
        request.user.is_superuser
        or getattr(request.user, "role", None) == "admin"
    ):

        context["base_template"] = "admin_app/base.html"

    # ======================================
    # AGENCY
    # ======================================

    elif request.user.role == "agency":

        context["base_template"] = (
            "agencies/base_agencies.html"
        )

        if hasattr(
            request.user,
            "agencyprofile"
        ):
            context["agency"] = (
                request.user.agencyprofile
            )

    # ======================================
    # RESTAURANT
    # ======================================

    elif request.user.role == "restaurant":

        context["base_template"] = (
            "restaurants/base_restaurant.html"
        )

        if hasattr(
            request.user,
            "restaurantprofile"
        ):
            context["restaurant"] = (
                request.user.restaurantprofile
            )

    # ======================================
    # TRAVELLER
    # ======================================

    else:

        context["base_template"] = (
            "travellers/base.html"
        )

        if hasattr(
            request.user,
            "travellerprofile"
        ):
            context["traveller"] = (
                request.user.travellerprofile
            )

    return render(
        request,
        "community/notifications.html",
        context
    )


@login_required
def get_unread_notifications_count(request):
    """API endpoint to get unread notifications count"""
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'unread_count': unread_count})


@login_required
def get_recent_notifications(request):
    """API endpoint to get recent notifications for dropdown"""
    
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related(
        'sender',
        'buddy_request',
        'profile_post'
    ).order_by('-created_at')[:10]

    notifications_data = []

    for notif in notifications:
        data = {
            'id': notif.id,
            'type': notif.notification_type,
            'message': notif.message,
            'created_at': notif.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'is_read': notif.is_read,
        }

        # Sender Details
        if notif.sender:
            sender_name = None
            if hasattr(notif.sender, 'get_display_name'):
                sender_name = notif.sender.get_display_name()
            elif hasattr(notif.sender, 'get_full_name'):
                sender_name = notif.sender.get_full_name()
            elif hasattr(notif.sender, 'username'):
                sender_name = notif.sender.username
            else:
                sender_name = 'User'
            
            data['sender_name'] = sender_name

            # Sender Avatar
            avatar_url = None
            if hasattr(notif.sender, 'profile_picture') and notif.sender.profile_picture:
                avatar_url = notif.sender.profile_picture.url
            elif hasattr(notif.sender, 'travellerprofile') and notif.sender.travellerprofile.profile_picture:
                avatar_url = notif.sender.travellerprofile.profile_picture.url
            elif hasattr(notif.sender, 'agencyprofile') and notif.sender.agencyprofile.profile_picture:
                avatar_url = notif.sender.agencyprofile.profile_picture.url
            
            data['sender_avatar'] = avatar_url

        # Buddy Request - IMPORTANT: Check the related object
        if notif.buddy_request:
            data['buddy_request_id'] = notif.buddy_request.id
            data['buddy_request_status'] = notif.buddy_request.status
        elif notif.request and notif.request.buddy_request:
            # Alternative: if buddy_request is stored in a generic way
            data['buddy_request_id'] = notif.request.id if hasattr(notif.request, 'id') else None

        notifications_data.append(data)

    return JsonResponse({
        'notifications': notifications_data
    })


@login_required
def mark_notification_read(request, notification_id):
    """
    Mark a single notification as read
    """

    if request.method == "POST":

        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.user
        )

        notification.is_read = True
        notification.save()

        # ==================================================
        # BUDDY REQUESTS
        # ==================================================

        if notification.notification_type == "buddy_request":

            return redirect(
                "travellers:buddy_requests"
            )

        elif notification.notification_type == "buddy_request_accepted":

            if notification.sender:

                return redirect(
                    "travellers:public_profile",
                    user_id=notification.sender.id
                )

        elif notification.notification_type == "buddy_request_rejected":

            return redirect(
                "community:notifications"
            )

        # ==================================================
        # PROFILE POSTS
        # ==================================================

        elif (
            notification.notification_type == "profile_like"
            and notification.profile_post
        ):

            return redirect(
                "travellers:user_profile",
                user_id=notification.profile_post.user.id
            )

        elif (
            notification.notification_type == "profile_comment"
            and notification.profile_post
        ):

            return redirect(
                "travellers:user_profile",
                user_id=notification.profile_post.user.id
            )

        # ==================================================
        # DESTINATION APPROVALS
        # ==================================================

        elif notification.notification_type in [
            "destination_approved",
            "destination_rejected"
        ]:

            if (
                notification.content_object
                and hasattr(notification.content_object, "id")
            ):

                return redirect(
                    "destinations:destination_detail",
                    destination_id=notification.content_object.id
                )

        # ==================================================
        # PLACE APPROVALS
        # ==================================================

        elif notification.notification_type in [
            "place_approved",
            "place_rejected"
        ]:

            place = notification.content_object

            if place:

                return redirect(
                    "destinations:place_detail",
                    destination_id=place.destination.id,
                    place_id=place.id
                )

        # ==================================================
        # COMPLAINT NOTIFICATIONS (USER)
        # ==================================================

        elif notification.notification_type in [
            "complaint_response",
            "complaint_resolved",
        ]:

            complaint = notification.content_object

            if complaint:

                return redirect(
                    "support:complaint_detail",
                    complaint_id=complaint.id
                )

        # ==================================================
        # COMPLAINT NOTIFICATIONS (ADMIN)
        # ==================================================

        elif notification.notification_type == "complaint_created":

            complaint = notification.content_object

            if complaint:

                return redirect(
                    "support:complaint_detail_admin",
                    complaint_id=complaint.id
                )

        # ==================================================
        # FOLLOW NOTIFICATIONS
        # ==================================================

        elif notification.notification_type == "follow":

            if notification.sender:

                return redirect(
                    "travellers:public_profile",
                    user_id=notification.sender.id
                )

        # ==================================================
        # MESSAGE NOTIFICATIONS
        # ==================================================

        elif notification.notification_type == "message":

            return redirect(
                "community:notifications"
            )

        # ==================================================
        # DEFAULT
        # ==================================================

        return redirect(
            "community:notifications"
        )

    return redirect(
        "community:notifications"
    )


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@login_required
def create_post(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    is_member = community.members.filter(user=request.user).exists()
    is_creator = community.creator == request.user

    if not is_member and not is_creator:
        messages.error(request, "You must join this community to create posts.")
        return redirect('community:community_detail', pk=community.id)

    if request.method == "POST":
        form = PostForm(request.POST)

        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.community = community
            post.save()

            # ✅ Directly grab all uploaded images — no formset needed
            images = request.FILES.getlist('images')
            for image in images:
                PostImage.objects.create(post=post, image=image)

            # Handle optional poll
            poll_question = request.POST.get('poll_question', '').strip()
            poll_options = [o.strip() for o in request.POST.getlist('poll_options') if o.strip()]

            if poll_question and len(poll_options) >= 2:
                poll = Poll.objects.create(
                    community=community,
                    user=request.user,
                    question=poll_question
                )
                for option_text in poll_options:
                    PollOption.objects.create(poll=poll, option_text=option_text)
                messages.success(request, "Post with poll created successfully!")
            else:
                messages.success(request, "Post created successfully!")

            return redirect('community:community_detail', pk=community.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PostForm()

    context = {
        'form': form,
        'community': community,
    }
    return render(request, "community/create_post.html", context)


def community_detail(request, pk):
    community = get_object_or_404(Community, id=pk)
    
    # Get members count
    members_count = community.members.count()
    
    # Get members list (for sidebar)
    members = community.members.select_related('user').all()[:10]
    
    posts = Post.objects.filter(community=community).select_related('user').prefetch_related('images', 'comments')
    
    polls = Poll.objects.filter(community=community)
    
    trips = Trip.objects.filter(community=community)
    
    # Check if current user is a member
    is_member = False
    has_pending_request = False
    pending_requests = []
    
    if request.user.is_authenticated:
        is_member = CommunityMember.objects.filter(
            user=request.user, 
            community=community
        ).exists()
        
        # Check if user has pending join request
        has_pending_request = JoinRequest.objects.filter(
            user=request.user,
            community=community,
            status='pending'
        ).exists()
        
        # Get pending requests for creator
        if request.user == community.creator:
            pending_requests = JoinRequest.objects.filter(
                community=community,
                status='pending'
            ).select_related('user')
    
    context = {
        "community": community,
        "posts": posts,
        "polls": polls,
        "trips": trips,
        "members_count": members_count,
        "members": members,
        "is_member": is_member,
        "has_pending_request": has_pending_request,
        "pending_requests": pending_requests,
    }
    
    return render(request, "community/community_detail.html", context)


@login_required
def join_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if request.user == trip.creator:
        messages.warning(request, "You created this trip.")
        return redirect("community:trip_detail", id=trip.id)

    existing = TripParticipant.objects.filter(
        trip=trip,
        user=request.user
    ).first()

    if existing:
        messages.info(request, f"Status: {existing.status}")
        return redirect("community:trip_detail", id=trip.id)

    # Create participant
    participant = TripParticipant.objects.create(
        trip=trip,
        user=request.user,
        status="approved" if trip.join_type == "direct" else "pending"
    )

    # Auto add to chat
    if participant.status == "approved":
        room = get_or_create_trip_room(trip)
        room.participants.add(request.user)

    # Notify creator
    Notification.objects.create(
        user=trip.creator,
        message=f"{request.user.username} requested to join {trip.title}",
        notification_type="trip_update"
    )

    messages.success(request, "Join request sent!")
    return redirect("community:trip_detail", id=trip.id)


@login_required
def create_trip(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    
    # Check if user is a member of the community
    is_member = CommunityMember.objects.filter(
        user=request.user, 
        community=community
    ).exists()
    
    if not is_member:
        messages.error(request, "You must be a member of this community to create a trip.")
        return redirect('community:community_detail', pk=community.id)
    
    if request.method == "POST":
        form = TripForm(request.POST)
        image_formset = TripImageFormSet(request.POST, request.FILES, queryset=TripImage.objects.none())
        itinerary_formset = TripItineraryFormSet(request.POST, queryset=TripItinerary.objects.none())
        
        print("Form data:", request.POST)  # Debug - check what's being submitted
        print("Form is valid:", form.is_valid())  # Debug
        print("Form errors:", form.errors)  # Debug
        
        if form.is_valid() and image_formset.is_valid() and itinerary_formset.is_valid():
            try:
                trip = form.save(commit=False)
                trip.creator = request.user
                trip.community = community
                trip.save()

                create_audit_log(
                    user=request.user,
                    action='trip_created',
                    description=f'Created trip: {trip.title}'
                )
                
                # Creator auto participant
                TripParticipant.objects.create(
                    trip=trip,
                    user=request.user,
                    role="coordinator",
                    status="approved"
                )
                
                # Create chat room
                room = get_or_create_trip_room(trip)
                room.participants.add(request.user)
                
                # Save images
                for f in image_formset:
                    if f.cleaned_data and f.cleaned_data.get('image'):
                        TripImage.objects.create(
                            trip=trip,
                            image=f.cleaned_data['image']
                        )
                
                # Save itinerary
                for f in itinerary_formset:
                    if f.cleaned_data and f.cleaned_data.get('title'):
                        TripItinerary.objects.create(
                            trip=trip,
                            day_number=f.cleaned_data.get("day_number"),
                            title=f.cleaned_data["title"],
                            description=f.cleaned_data["description"]
                        )
                
                messages.success(request, f'Trip "{trip.title}" created successfully!')
                return redirect("community:community_detail", pk=community.id)
                
            except Exception as e:
                print("Error creating trip:", str(e))  # Debug
                messages.error(request, f"Error creating trip: {str(e)}")
                return redirect("community:create_trip", community_id=community.id)
        else:
            # Print detailed errors for debugging
            print("Form errors:", form.errors)
            print("Image formset errors:", image_formset.errors)
            print("Itinerary formset errors:", itinerary_formset.errors)
            messages.error(request, "Please correct the errors below.")
    
    else:
        form = TripForm()
        image_formset = TripImageFormSet(queryset=TripImage.objects.none())
        itinerary_formset = TripItineraryFormSet(queryset=TripItinerary.objects.none())
    
    context = {
        "form": form,
        "image_formset": image_formset,
        "itinerary_formset": itinerary_formset,
        "community": community,
    }
    
    return render(request, "community/create_trip.html", context)


def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    like, created = PostLike.objects.get_or_create(
        user=request.user,
        post=post
    )

    if not created:
        like.delete()  # toggle (unlike)
    
    if created and post.user != request.user:
        Notification.objects.create(
            user=post.user,
            message=f"{request.user.username} liked your post",
            notification_type="post_like"
        )

    return redirect('community:community_detail', pk=post.community.id)


def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        text = request.POST.get("text")

        Comment.objects.create(
            post=post,
            user=request.user,
            text=text
        )

    if post.user != request.user:
        Notification.objects.create(
            user=post.user,
            message=f"{request.user.username} commented on your post",
            notification_type="comment"
        )

    return redirect('community:community_detail', pk=post.community.id)


@login_required
def edit_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.user != community.creator:
        return redirect("community:community_detail", pk=community.id)

    if request.method == "POST":
        form = CommunityForm(request.POST, request.FILES, instance=community)

        if form.is_valid():
            form.save()
            return redirect("community:community_detail", pk=community.id)
    else:
        form = CommunityForm(instance=community)

    return render(request, "community/edit_community.html", {
        "form": form,
        "community": community
    })


@login_required
def delete_item(request, item_type, item_id):
    if request.method != "POST":
        return redirect("community:community_list")

    # POST
    if item_type == "post":
        item = get_object_or_404(Post, id=item_id)
        community = item.community

        can_delete = (
            request.user == item.user or
            request.user == community.creator
        )

    elif item_type == "poll":
        item = get_object_or_404(Poll, id=item_id)
        community = item.community

        # Change this if Poll uses creator instead of user
        poll_owner = getattr(item, "user", None) or getattr(item, "creator", None)

        can_delete = (
            request.user == poll_owner or
            request.user == community.creator
        )

    elif item_type == "trip":
        item = get_object_or_404(Trip, id=item_id)
        community = item.community

        can_delete = (
            request.user == item.creator or
            (community and request.user == community.creator)
        )

    else:
        return redirect("community:community_list")

    if not can_delete:
        return HttpResponseForbidden("You do not have permission to delete this item.")

    # Save community before deletion
    community_id = community.id if community else None

    item.delete()

    # Redirect after deletion
    if community_id:
        return redirect(
            "community:community_detail",
            pk=community_id
        )

    # Private trip
    if item_type == "trip":
        return redirect("community:private_trip_list")

    return redirect("community:community_list")

@login_required
def community_members(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    members = CommunityMember.objects.filter(community=community)

    return render(request, "community/members.html", {
        "community": community,
        "members": members
    })


def delete_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.user == community.creator:
        community_name = community.name
        create_audit_log(
        user=request.user,
        action='community_deleted',
        description=f'Deleted community: {community_name}'
        )
        community.delete()



    return redirect("community:community_list")


@login_required
def vote_poll(request, option_id):
    option = get_object_or_404(PollOption, id=option_id)
    poll = option.poll

    # prevent multiple votes
    PollVote.objects.filter(poll=poll, user=request.user).delete()

    PollVote.objects.create(
        poll=poll,
        option=option,
        user=request.user
    )

    if poll.user != request.user:
        Notification.objects.create(
            user=poll.user,
            message=f"{request.user.username} voted on your poll",
            notification_type="poll_vote"
        )

    return redirect('community:community_detail', pk=poll.community.id)


@login_required
def create_poll(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.method == "POST":
        question = request.POST.get("question")
        options = request.POST.getlist("options")
        images = request.FILES.getlist("option_images")

        poll = Poll.objects.create(
            community=community,
            user=request.user,
            question=question
        )

        for i, opt in enumerate(options):
            img = images[i] if i < len(images) else None
            if opt:
                PollOption.objects.create(
                    poll=poll,
                    option_text=opt,
                    image=img
                )

        return redirect('community:community_detail', pk=community.id)

    return render(request, "community/create_poll.html", {
        "community": community
    })


@login_required
def trip_detail(request, id):
    from community.models import Trip, TripParticipant, TripImage, TripItinerary
    from travellers.models import BuddyRequest
    
    # Get trip with all related data
    trip = get_object_or_404(
        Trip.objects.prefetch_related(
            'images',  # This should work with related_name="images"
            'itineraries',
            'participants__user'
        ), 
        id=id
    )

    # Debug - print to console to check if images exist
    print(f"=== TRIP DETAIL DEBUG ===")
    print(f"Trip ID: {trip.id}")
    print(f"Trip Title: {trip.title}")
    print(f"Images count: {trip.images.count()}")
    for img in trip.images.all():
        print(f"  - Image URL: {img.image.url}")
    print(f"=========================")

    seats_left = trip.max_members - trip.participants.count()
    is_owner = request.user == trip.creator

    participants = trip.participants.select_related("user").all()

    is_joined = TripParticipant.objects.filter(
        trip=trip,
        user=request.user
    ).exists()
    
    # Check if user is a coordinator
    user_participant = TripParticipant.objects.filter(
        trip=trip,
        user=request.user
    ).first()
    is_coordinator = user_participant and user_participant.role == 'coordinator' if user_participant else False

    can_view_map = is_owner or is_coordinator
    
    # Check buddy relationships for message permissions
    buddy_ids = []
    is_buddy = False
    
    if request.user.is_authenticated and not is_owner:
        buddy_requests = BuddyRequest.objects.filter(
            from_user=request.user,
            status='accepted'
        ).values_list('to_user_id', flat=True)
        
        buddy_requests2 = BuddyRequest.objects.filter(
            to_user=request.user,
            status='accepted'
        ).values_list('from_user_id', flat=True)
        
        buddy_ids = list(buddy_requests) + list(buddy_requests2)
        is_buddy = trip.creator.id in buddy_ids
    
    # Order itineraries by day_number
    itineraries = trip.itineraries.all().order_by('day_number')
    
    # Get images as a list to ensure they're loaded
    images = list(trip.images.all())

    return render(request, "community/trip_details.html", {
        "trip": trip,
        "is_joined": is_joined,
        "is_owner": is_owner,
        "is_coordinator": is_coordinator,
        "seats_left": seats_left,
        "participants": participants,
        "can_view_map": can_view_map,
        "itineraries": itineraries,
        "buddy_ids": buddy_ids,
        "is_buddy": is_buddy,
        "images": images,  # Pass as list to template
        "has_images": len(images) > 0,
    })


@login_required
def cancel_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    participant = TripParticipant.objects.filter(
        trip=trip,
        user=request.user
    ).first()

    if participant:
        # Remove from room
        room = ChatRoom.objects.filter(trip=trip).first()
        if room:
            room.participants.remove(request.user)

        participant.delete()

        Notification.objects.create(
            user=trip.creator,
            message=f"{request.user.username} cancelled the trip {trip.title}",
            notification_type="trip_update"
        )

    return redirect("community:trip_detail", id=trip.id)


@login_required
def edit_trip(request, trip_id):
    from .forms import TripImageFormSet, TripItineraryFormSet
    
    trip = get_object_or_404(Trip, id=trip_id)

    if request.user != trip.creator:
        return redirect("community:trip_detail", id=trip.id)

    # Get existing images and itinerary
    existing_images = TripImage.objects.filter(trip=trip)
    existing_itinerary = TripItinerary.objects.filter(trip=trip).order_by('day_number')
    
    # Create itinerary data for JavaScript
    itinerary_data = []
    for itinerary in existing_itinerary:
        itinerary_data.append({
            'day_number': itinerary.day_number,
            'title': itinerary.title,
            'description': itinerary.description
        })
    
    if request.method == "POST":
        form = TripForm(request.POST, instance=trip)
        
        # Create formset with FILES
        image_formset = TripImageFormSet(request.POST, request.FILES, queryset=TripImage.objects.none())
        
        print("=== EDIT TRIP DEBUG ===")
        print(f"POST keys: {request.POST.keys()}")
        print(f"FILES keys: {request.FILES.keys()}")
        print(f"FILES: {request.FILES}")
        print(f"Form is valid: {form.is_valid()}")
        print(f"Image formset is valid: {image_formset.is_valid()}")
        print(f"Image formset errors: {image_formset.errors}")
        
        if form.is_valid() and image_formset.is_valid():
            try:
                trip = form.save()
                print(f"Trip saved: {trip.id}")
                
                # Handle existing image deletions
                delete_images = request.POST.get('delete_images', '')
                if delete_images:
                    image_ids = [int(id) for id in delete_images.split(',') if id]
                    deleted = TripImage.objects.filter(id__in=image_ids, trip=trip).delete()
                    print(f"Deleted images: {deleted}")
                
                # Save new images from formset
                saved_count = 0
                for i, f in enumerate(image_formset):
                    if f.cleaned_data and f.cleaned_data.get('image'):
                        image_file = f.cleaned_data['image']
                        img = TripImage.objects.create(
                            trip=trip,
                            image=image_file
                        )
                        saved_count += 1
                        print(f"Saved image {i}: {img.image.url}")
                
                print(f"Total new images saved: {saved_count}")
                
                # Handle itinerary updates
                days = int(request.POST.get('duration_days', 0))
                TripItinerary.objects.filter(trip=trip).delete()
                
                for i in range(days):
                    title = request.POST.get(f'itinerary-{i}-title', '')
                    description = request.POST.get(f'itinerary-{i}-description', '')
                    if title and description:
                        TripItinerary.objects.create(
                            trip=trip,
                            day_number=i + 1,
                            title=title,
                            description=description
                        )
                
                messages.success(request, "Trip updated successfully!")
                return redirect("community:trip_detail", id=trip.id)
                
            except Exception as e:
                print(f"Error: {str(e)}")
                messages.error(request, f"Error updating trip: {str(e)}")
        else:
            print(f"Form errors: {form.errors}")
            print(f"Image formset errors: {image_formset.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = TripForm(instance=trip)
        image_formset = TripImageFormSet(queryset=TripImage.objects.none())
    
    context = {
        'form': form,
        'image_formset': image_formset,
        'trip': trip,
        'existing_images': existing_images,
        'existing_itinerary': existing_itinerary,
        'existing_itinerary_json': json.dumps(itinerary_data),
    }
    
    return render(request, "community/edit_trip.html", context)

@login_required
def trip_chat(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    room = get_or_create_trip_room(trip)

    # permission check
    if request.user not in room.participants.all():
        return redirect("community:trip_detail", id=trip.id)

    # Redirect to inbox
    return redirect(f"/traveller/inbox/?room={room.id}")


@login_required
def approve_participant(request, participant_id):
    participant = get_object_or_404(TripParticipant, id=participant_id)

    if request.user != participant.trip.creator:
        return HttpResponseForbidden()

    participant.status = "approved"
    participant.save()

    # Add to room
    room = get_or_create_trip_room(participant.trip)
    room.participants.add(participant.user)

    Notification.objects.create(
        user=participant.user,
        message=f"You were approved for {participant.trip.title}",
        notification_type="trip_update"
    )

    return redirect("community:trip_detail", id=participant.trip.id)


def reject_participant(request, participant_id):
    participant = get_object_or_404(TripParticipant, id=participant_id)

    if request.user != participant.trip.creator:
        return HttpResponseForbidden()

    participant.status = "rejected"
    participant.save()

    Notification.objects.create(
        user=participant.user,
        message=f"Your request was rejected for {participant.trip.title}",
        notification_type="trip_update"
    )

    return redirect("community:trip_detail", id=participant.trip.id)


@login_required
def remove_participant(request, participant_id):
    participant = get_object_or_404(TripParticipant, id=participant_id)

    if request.user != participant.trip.creator:
        return HttpResponseForbidden()

    user = participant.user
    trip = participant.trip

    # Remove from room
    room = ChatRoom.objects.filter(trip=trip).first()
    if room:
        room.participants.remove(user)

    participant.delete()

    Notification.objects.create(
        user=user,
        message=f"You were removed from {trip.title}",
        notification_type="trip_update"
    )

    return redirect("community:trip_detail", id=trip.id)


def get_or_create_trip_room(trip):
    room, created = ChatRoom.objects.get_or_create(
        trip=trip,
        defaults={
            "type": "group",
            "name": trip.title
        }
    )

    if created:
        room.participants.add(trip.creator)

    return room


@login_required
def update_location(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"})

    data = json.loads(request.body)

    trip_id = data.get("trip_id")

    participant = TripParticipant.objects.filter(
        trip_id=trip_id,
        user=request.user,
        status="approved"
    ).first()

    if not participant:
        return JsonResponse({"error": "Unauthorized"})

    participant.is_location_sharing = True
    participant.save()

    LiveLocation.objects.update_or_create(
        participant=participant,
        defaults={
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "accuracy": data.get("accuracy")
        }
    )

    return JsonResponse({"status": "success"})


@login_required
def create_private_trip(request):
    from .forms import TripImageFormSet, TripItineraryFormSet
    
    if request.method == "POST":
        form = TripForm(request.POST)
        image_formset = TripImageFormSet(request.POST, request.FILES, queryset=TripImage.objects.none())
        itinerary_formset = TripItineraryFormSet(request.POST, queryset=TripItinerary.objects.none())
        
        print("Form data:", request.POST)
        print("Files:", request.FILES)
        print("Form is valid:", form.is_valid())
        print("Form errors:", form.errors)
        print("Image formset is valid:", image_formset.is_valid())
        print("Image formset errors:", image_formset.errors)
        print("Itinerary formset is valid:", itinerary_formset.is_valid())
        print("Itinerary formset errors:", itinerary_formset.errors)
        
        if form.is_valid() and image_formset.is_valid() and itinerary_formset.is_valid():
            try:
                trip = form.save(commit=False)
                trip.creator = request.user
                trip.visibility = "private"
                trip.join_type = "invite_only"
                trip.community = None
                trip.save()
                
                create_audit_log(
                    user=request.user,
                    action='trip_created',
                    description=f'Created trip: {trip.title}'
                )
                # Add creator as participant
                TripParticipant.objects.create(
                    trip=trip,
                    user=request.user,
                    role="coordinator",
                    status="approved"
                )
                
                # Create chat room
                room = get_or_create_trip_room(trip)
                room.participants.add(request.user)
                
                # Save images
                for f in image_formset:
                    if f.cleaned_data and f.cleaned_data.get('image'):
                        TripImage.objects.create(
                            trip=trip,
                            image=f.cleaned_data['image']
                        )
                
                # Save itinerary
                for f in itinerary_formset:
                    if f.cleaned_data and f.cleaned_data.get('title'):
                        TripItinerary.objects.create(
                            trip=trip,
                            day_number=f.cleaned_data.get("day_number", 0),
                            title=f.cleaned_data["title"],
                            description=f.cleaned_data["description"]
                        )
                
                messages.success(request, f'Private trip "{trip.title}" created successfully!')
                return redirect("community:private_trip_list")
                
            except Exception as e:
                print("Error creating private trip:", str(e))
                messages.error(request, f"Error creating private trip: {str(e)}")
                return redirect("community:create_private_trip")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TripForm()
        image_formset = TripImageFormSet(queryset=TripImage.objects.none())
        itinerary_formset = TripItineraryFormSet(queryset=TripItinerary.objects.none())
    
    context = {
        "form": form,
        "image_formset": image_formset,
        "itinerary_formset": itinerary_formset,
    }
    
    return render(request, "community/create_private_trip.html", context)


@login_required
def join_private_trip(request, invite_code):
    trip = get_object_or_404(
        Trip,
        invite_code=invite_code
    )

    existing = TripParticipant.objects.filter(
        trip=trip,
        user=request.user
    ).exists()

    if existing:
        return redirect("community:trip_detail", id=trip.id)

    participant = TripParticipant.objects.create(
        trip=trip,
        user=request.user,
        status="approved"
    )

    room = get_or_create_trip_room(trip)
    room.participants.add(request.user)

    return redirect("community:trip_detail", id=trip.id)


@login_required
def get_trip_locations(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    participant = TripParticipant.objects.filter(
        trip=trip,
        user=request.user,
        status="approved"
    ).first()

    if not participant:
        return JsonResponse({"error": "Unauthorized"})

    participants = TripParticipant.objects.filter(
        trip=trip,
        status="approved",
        is_location_sharing=True
    ).select_related("user")

    data = []

    for p in participants:
        if hasattr(p, "location"):
            data.append({
                "username": p.user.username,
                "latitude": p.location.latitude,
                "longitude": p.location.longitude,
            })

    return JsonResponse(data, safe=False)


@login_required
def private_trip_list(request):
    # Trips I created
    created_trips = Trip.objects.filter(
        creator=request.user,
        visibility="private"
    ).prefetch_related('participants', 'images').order_by("-created_at")
 
    # Trips I joined (but didn't create)
    joined_trips = Trip.objects.filter(
        visibility="private",
        participants__user=request.user
    ).exclude(
        creator=request.user
    ).distinct().prefetch_related('participants', 'images').order_by("-created_at")
 
    return render(request, "community/private_trip_list.html", {
        "created_trips": created_trips,
        "joined_trips": joined_trips,
        # keep a combined list for any template that uses `trips`
        "trips": list(created_trips) + list(joined_trips),
    })


def get_trip_invite_link(request, trip):
    return request.build_absolute_uri(
        f"/community/trip/invite/{trip.invite_code}/"
    )


@login_required
def invite_trip_page(request, invite_code):
    trip = get_object_or_404(Trip, invite_code=invite_code)

    # already joined check
    already = TripParticipant.objects.filter(
        trip=trip,
        user=request.user
    ).exists()

    if not already:
        TripParticipant.objects.create(
            trip=trip,
            user=request.user,
            status="approved" if trip.join_type == "direct" else "pending"
        )

        room = get_or_create_trip_room(trip)

        if trip.join_type == "direct":
            room.participants.add(request.user)

    return redirect("community:trip_detail", id=trip.id)


@login_required
def trip_live_map(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    participant = TripParticipant.objects.filter(
        trip=trip,
        user=request.user,
        status="approved"
    ).first()

    if not participant:
        return JsonResponse({"error": "Unauthorized"})

    return render(request, "community/live_tracking.html", {
        "trip": trip
    })

@login_required
def request_join_community(request, community_id):
    """Request to join a private community"""
    community = get_object_or_404(Community, id=community_id)
    
    # Check if already a member
    if CommunityMember.objects.filter(user=request.user, community=community).exists():
        messages.warning(request, "You are already a member of this community")
        return redirect('community:community_detail', pk=community.id)
    
    # Check if request already exists
    existing_request = JoinRequest.objects.filter(
        user=request.user, 
        community=community,
        status='pending'
    ).first()
    
    if existing_request:
        messages.info(request, "You already have a pending request")
        return redirect('community:community_detail', pk=community.id)
    
    # Create join request
    join_request = JoinRequest.objects.create(
        user=request.user,
        community=community,
        status='pending'
    )
    
    # Notify community creator
    Notification.objects.create(
        user=community.creator,
        community=community,
        request=join_request,
        message=f"{request.user.username} requested to join {community.name}",
        notification_type="join_request"
    )
    
    messages.success(request, f"Your request to join {community.name} has been sent!")
    return redirect('community:community_detail', pk=community.id)

@login_required
def reject_request(request, request_id):
    """Reject a join request"""
    join_request = get_object_or_404(JoinRequest, id=request_id)
    
    # Check permission (only creator can reject)
    if request.user != join_request.community.creator:
        return HttpResponseForbidden()
    
    # Update status
    join_request.status = 'rejected'
    join_request.save()

    create_audit_log(
        user=request.user,
        action='join_request_rejected',
        description=f'Rejected join request for {join_request.user.username} in {join_request.community.name}'
    )
    
    # Notify the user
    Notification.objects.create(
        user=join_request.user,
        community=join_request.community,
        message=f"Your request to join {join_request.community.name} was declined",
        notification_type="request_rejected"
    )
    
    messages.success(request, f"Request from {join_request.user.username} rejected")
    return redirect('community:community_detail', pk=join_request.community.id)


from django.http import HttpResponseForbidden
from admin_app.utils import create_audit_log

@login_required
def accept_request(request, request_id):

    join_request = get_object_or_404(
        JoinRequest,
        id=request_id
    )

    # Only community creator can approve
    if request.user != join_request.community.creator:
        return HttpResponseForbidden()

    # Already processed
    if join_request.status == "approved":
        messages.warning(
            request,
            "Request already approved."
        )
        return redirect(
            "community:community_detail",
            pk=join_request.community.id
        )

    # Approve request
    join_request.status = "approved"
    join_request.save()

    # Audit Log
    create_audit_log(
        user=request.user,
        action='join_request_approved',
        description=(
            f'Approved join request for '
            f'{join_request.user.username} '
            f'in {join_request.community.name}'
        )
    )

    # Add community member if not already added
    if not CommunityMember.objects.filter(
        user=join_request.user,
        community=join_request.community
    ).exists():

        CommunityMember.objects.create(
            user=join_request.user,
            community=join_request.community
        )

    # Notify creator
    Notification.objects.create(
        user=request.user,
        community=join_request.community,
        request=join_request,
        message=(
            f"You accepted "
            f"{join_request.user.username}'s request "
            f"to join {join_request.community.name}"
        ),
        notification_type="request_approved"
    )

    # Notify member
    Notification.objects.create(
        user=join_request.user,
        community=join_request.community,
        message=(
            f"Your request to join "
            f"{join_request.community.name} was accepted!"
        ),
        notification_type="request_approved"
    )

    messages.success(
        request,
        f"Added {join_request.user.username} to the community"
    )

    return redirect(
        "community:community_detail",
        pk=join_request.community.id
    )


@login_required
def promote_to_coordinator(request, participant_id):
    """Promote a participant to coordinator role"""
    participant = get_object_or_404(TripParticipant, id=participant_id)
    
    # Check if current user is the trip creator
    if request.user != participant.trip.creator:
        messages.error(request, "Only the trip creator can promote coordinators.")
        return redirect("community:trip_detail", id=participant.trip.id)
    
    # Promote to coordinator
    participant.role = "coordinator"
    participant.save()
    
    # Notify the user
    Notification.objects.create(
        user=participant.user,
        message=f"You have been promoted to coordinator for trip '{participant.trip.title}'",
        notification_type="trip_update"
    )
    
    messages.success(request, f"{participant.user.username} has been promoted to coordinator.")
    return redirect("community:trip_detail", id=participant.trip.id)