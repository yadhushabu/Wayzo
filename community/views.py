
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import ChatRoom, Community, CommunityMember, JoinRequest, Notification, Poll, PollOption, PollVote, Post, PostImage, PostLike, Trip, TripImage, TripItinerary, TripParticipant, Comment, Message
from .forms import CommunityForm, PostForm, PostImageFormSet, TripForm, TripImageFormSet, TripItineraryFormSet
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def community_home(request):

    # communities created by user
    created_communities = Community.objects.filter(
        creator=request.user
    )

    # communities joined by user
    joined_communities = Community.objects.filter(
        members__user=request.user
    ).exclude(
        creator=request.user
    ).distinct()

    # notifications
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, "community/community_home.html", {
        "created_communities": created_communities,
        "joined_communities": joined_communities,
        "notifications": notifications,
    })

@login_required
def create_community(request):

    if request.method == "POST":
        form = CommunityForm(request.POST, request.FILES)
        if form.is_valid():
            community = form.save(commit=False)
            community.creator = request.user
            community.save()

            # creator becomes member + admin
            CommunityMember.objects.create(
                user=request.user,
                community=community,
                is_admin=True
            )

            return redirect("community_home")
    else:
        form = CommunityForm()

    return render(request, "community/create_community.html", {"form": form})

def community_list(request):
    communities = Community.objects.all()

    if request.user.is_authenticated:
        joined_ids = CommunityMember.objects.filter(
            user=request.user
        ).values_list("community_id", flat=True)

        communities = communities.exclude(id__in=joined_ids)
        communities = communities.exclude(creator=request.user)  # ✅ NEW

    return render(request, "community/community_list.html", {
        "communities": communities
    })

@login_required
def join_community(request, community_id):

    community = get_object_or_404(Community, id=community_id)

    # already joined
    if CommunityMember.objects.filter(user=request.user, community=community).exists():
        return redirect("community_detail", pk=community.id)

    # ✅ PUBLIC → direct join
    if community.community_type == "public":

        CommunityMember.objects.create(
            user=request.user,
            community=community
        )

        # ✅ Notify USER
        Notification.objects.create(
            user=request.user,
            community=community,
            message=f"You joined {community.name}",
            notification_type="request_approved"
        )

    # ✅ Notify CREATOR
    if request.user != community.creator:
        Notification.objects.create(
            user=community.creator,
            community=community,
            message=f"{request.user.username} joined your community {community.name}",
            notification_type="request_approved"
        )

    # ✅ PRIVATE → send request
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

    return redirect("community_home")
@login_required
def accept_request(request, request_id):
    join_request = JoinRequest.objects.get(id=request_id)

    # approve request
    join_request.status = "approved"
    join_request.save()

    # add user to community
    CommunityMember.objects.create(
        user=join_request.user,
        community=join_request.community
    )

    # ❗ UPDATE notification for creator (YOU)
    Notification.objects.create(
        user=request.user,   # creator
        community=join_request.community,
        request=join_request,
        message=f"You accepted {join_request.user.username}'s request to join {join_request.community.name}",
        notification_type="request_approved"
    )

    # ✅ ALSO notify the user (optional but better UX)
    Notification.objects.create(
        user=join_request.user,
        community=join_request.community,
        message=f"Your request to join {join_request.community.name} was accepted",
        notification_type="request_approved"
    )

    return redirect("community_detail", pk=join_request.community.id)

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, "community/notifications.html", {
        "notifications": notifications
    })


@login_required
def create_post(request, community_id):

    community = get_object_or_404(Community, id=community_id)

    if request.method == "POST":
        form = PostForm(request.POST)
        image_formset = PostImageFormSet(
            request.POST,
            request.FILES,
            queryset=PostImage.objects.none()
        )

        if form.is_valid() and image_formset.is_valid():

            # ✅ SAVE POST
            post = form.save(commit=False)
            post.user = request.user
            post.community = community
            post.save()

            # ✅ SAVE POLL
            question = request.POST.get("poll_question", "").strip()
            options = request.POST.getlist("poll_options")

            valid_options = [opt.strip() for opt in options if opt.strip()]

            if question and len(valid_options) >= 2:
                poll = Poll.objects.create(
                    post=post,
                    question=question
                )

                for opt in valid_options:
                    PollOption.objects.create(
                        poll=poll,
                        option_text=opt
                    )

            # ✅ SAVE IMAGES
            for f in image_formset:
                if f.cleaned_data:
                    PostImage.objects.create(
                        post=post,
                        image=f.cleaned_data['image']
                    )

            return redirect("community_detail", pk=community.id)

    else:
        form = PostForm()
        image_formset = PostImageFormSet(queryset=PostImage.objects.none())

    return render(request, "community/create_post.html", {
        "form": form,
        "image_formset": image_formset,
        "community": community
    })
from django.shortcuts import get_object_or_404

def community_detail(request, pk):
    community = Community.objects.get(id=pk)

    posts = Post.objects.filter(community=community).select_related('user').prefetch_related('images', 'comments')

    # ✅ IMPORTANT
    polls = Poll.objects.filter(community=community)

    # ✅ IF YOU HAVE TRIPS MODEL
    trips = Trip.objects.filter(community=community)

    return render(request, "community/community_detail.html", {
        "community": community,
        "posts": posts,
        "polls": polls,
        "trips": trips   # ✅ ADD THIS
    })
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

@login_required
def join_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if request.user == trip.creator:
        messages.warning(request, "You created this trip.")
        return redirect("trip_detail", id=trip.id)

    existing = TripParticipant.objects.filter(trip=trip, user=request.user).first()

    if existing:
        messages.info(request, f"Status: {existing.status}")
        return redirect("trip_detail", id=trip.id)

    TripParticipant.objects.create(
        trip=trip,
        user=request.user,
        status="pending"
    )

    # 🔔 notify creator
    Notification.objects.create(
        user=trip.creator,
        message=f"{request.user.username} requested to join {trip.title}",
        notification_type="trip_request"
    )

    messages.success(request, "Join request sent!")

    return redirect("trip_detail", id=trip.id)

@login_required
def create_trip(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.method == "POST":
        form = TripForm(request.POST)
        image_formset = TripImageFormSet(request.POST, request.FILES, queryset=TripImage.objects.none())
        itinerary_formset = TripItineraryFormSet(request.POST)

        if form.is_valid() and image_formset.is_valid() and itinerary_formset.is_valid():

            trip = form.save(commit=False)
            trip.creator = request.user
            trip.community = community
            trip.save()

            # ✅ CREATE ROOM
            room = get_or_create_trip_room(trip)

            # images
            for f in image_formset:
                if f.cleaned_data:
                    TripImage.objects.create(
                        trip=trip,
                        image=f.cleaned_data['image']
                    )

            # itinerary
            for f in itinerary_formset:
                if f.cleaned_data:
                    TripItinerary.objects.create(
                        trip=trip,
                        day_number=f.cleaned_data["day_number"],
                        title=f.cleaned_data["title"],
                        description=f.cleaned_data["description"]
                    )

            return redirect("community_detail", pk=community.id)

    else:
        form = TripForm()
        image_formset = TripImageFormSet(queryset=TripImage.objects.none())
        itinerary_formset = TripItineraryFormSet(queryset=TripItinerary.objects.none())

    return render(request, "community/create_trip.html", {
        "form": form,
        "image_formset": image_formset,
        "itinerary_formset": itinerary_formset,
        "community": community
    })


from django.shortcuts import redirect, get_object_or_404
from .models import Post, PostLike

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

    return redirect('community_detail', pk=post.community.id)

from .models import Comment

def add_comment(request, post_id):
    post = Post.objects.get(id=post_id)

    if request.method == "POST":
        text = request.POST.get("text")

        Comment.objects.create(
            post=post,
            user=request.user,
            text=text   # ✅ FIXED
        )

    if post.user != request.user:
        Notification.objects.create(
            user=post.user,
            message=f"{request.user.username} commented on your post",
            notification_type="comment"
        )

    return redirect('community_detail', pk=post.community.id)
 

@login_required
def edit_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.user != community.creator:
        return redirect("community_detail", pk=community.id)

    if request.method == "POST":
        form = CommunityForm(request.POST, request.FILES, instance=community)

        if form.is_valid():
            form.save()
            return redirect("community_detail", pk=community.id)
    else:
        form = CommunityForm(instance=community)

    return render(request, "community/edit_community.html", {
        "form": form,
        "community": community
    })


@login_required
def delete_item(request, item_type, item_id):

    if request.method != "POST":
        return redirect("community_home")

    if item_type == "post":
        item = get_object_or_404(Post, id=item_id)
        community = item.community

    elif item_type == "poll":
        item = get_object_or_404(Poll, id=item_id)
        community = item.community

    elif item_type == "trip":
        item = get_object_or_404(Trip, id=item_id)
        community = item.community

    else:
        return redirect("community_home")

    if request.user == item.user or request.user == community.creator:
        item.delete()

    return redirect("community_detail", pk=community.id)



@login_required
def community_members(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    members = CommunityMember.objects.filter(community=community)

    return render(request, "community/members.html", {
        "community": community,
        "members": members
    })

from django.shortcuts import get_object_or_404, redirect

def delete_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.user == community.creator:
        community.delete()

    return redirect("community_list")

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

    return redirect('community_detail', pk=poll.community.id)


@login_required
def create_poll(request, community_id):
    community = Community.objects.get(id=community_id)

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

        return redirect('community_detail',pk=poll.community.id)

    return render(request, "community/create_poll.html", {
        "community": community
    })

@login_required
def trip_detail(request, id):
    trip = get_object_or_404(Trip, id=id)
    seats_left = trip.max_members - trip.participants.count()
    is_owner = request.user == trip.creator
    participants = trip.participants.select_related("user")

    is_joined = TripParticipant.objects.filter(
        trip=trip,
        user=request.user
    ).exists()

    return render(request, "community/trip_details.html", {
        "trip": trip,
        "is_joined": is_joined,
        "is_owner": is_owner,
        "seats_left": seats_left,
        "participants": participants
    })

@login_required
def cancel_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    participant = TripParticipant.objects.filter(
        trip=trip,
        user=request.user
    ).first()

    if participant:
        # ✅ REMOVE FROM ROOM
        room = ChatRoom.objects.filter(trip=trip).first()
        if room:
            room.participants.remove(request.user)

        participant.delete()

        Notification.objects.create(
            user=trip.creator,
            message=f"{request.user.username} cancelled the trip {trip.title}",
            notification_type="trip_update"
        )

    return redirect("trip_detail", id=trip.id)

@login_required
def edit_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if request.user != trip.creator:
        return redirect("trip_detail", id=trip.id)

    form = TripForm(request.POST or None, instance=trip)

    if form.is_valid():
        form.save()
        return redirect("trip_detail", id=trip.id)

    return render(request, "community/edit_trip.html", {
        "form": form,
        "trip": trip
    })



@login_required
def trip_chat(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    room = get_or_create_trip_room(trip)

    # permission check
    if request.user not in room.participants.all():
        return redirect("trip_detail", id=trip.id)

    # 👉 redirect to inbox
    return redirect(f"/traveller/inbox/?room={room.id}")


@login_required
def approve_participant(request, participant_id):
    participant = get_object_or_404(TripParticipant, id=participant_id)

    if request.user != participant.trip.creator:
        return HttpResponseForbidden()

    participant.status = "approved"
    participant.save()

    # ✅ ADD TO ROOM
    room = get_or_create_trip_room(participant.trip)
    room.participants.add(participant.user)

    Notification.objects.create(
        user=participant.user,
        message=f"You were approved for {participant.trip.title}",
        notification_type="trip_update"
    )

    return redirect("trip_detail", id=participant.trip.id)

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

    return redirect("trip_detail", id=participant.trip.id)


@login_required
def remove_participant(request, participant_id):
    participant = get_object_or_404(TripParticipant, id=participant_id)

    if request.user != participant.trip.creator:
        return HttpResponseForbidden()

    user = participant.user
    trip = participant.trip

    # ✅ REMOVE FROM ROOM
    room = ChatRoom.objects.filter(trip=trip).first()
    if room:
        room.participants.remove(user)

    participant.delete()

    Notification.objects.create(
        user=user,
        message=f"You were removed from {trip.title}",
        notification_type="trip_update"
    )

    return redirect("trip_detail", id=trip.id)
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