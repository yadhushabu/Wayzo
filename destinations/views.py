from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required

from .forms import DestinationForm, AttractionCostFormSet
from .models import Destination
from ai_engine.auto import generate_attractions


# ✅ CREATE DESTINATION (ADMIN ONLY)
@staff_member_required
def create_destination(request):

    if request.method == "POST":
        form = DestinationForm(request.POST, request.FILES)  # ✅ FIXED

        if form.is_valid():
            destination = form.save()
            generate_attractions(destination)

            messages.success(request, f'✨ "{destination.name}" created!')
            return redirect("destination_detail", slug=destination.slug)

    else:
        form = DestinationForm()

    return render(request, "destinations/create.html", {"form": form})

# ✅ LIST DESTINATIONS
def destination_list(request):

    destinations = Destination.objects.all().order_by("-id")

    return render(request, "destinations/list.html", {
        "destinations": destinations
    })


# ✅ DETAIL PAGE
def destination_detail(request, slug):

    destination = get_object_or_404(Destination, slug=slug)

    return render(request, "destinations/detail.html", {
        "destination": destination
    })

from .models import Destination, Attraction
from .forms import AttractionForm


def add_attraction(request, slug):

    destination = get_object_or_404(Destination, slug=slug)

    if request.method == "POST":
        form = AttractionForm(request.POST, request.FILES)
        formset = AttractionCostFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            attraction = form.save(commit=False)
            attraction.destination = destination
            attraction.save()

            formset.instance = attraction
            formset.save()

            messages.success(request, "Attraction added with costs ✅")
            return redirect("destination_detail", slug=slug)

    else:
        form = AttractionForm()
        formset = AttractionCostFormSet()

    return render(request, "destinations/add_attraction.html", {
        "form": form,
        "formset": formset,
        "destination": destination
    })


from django.contrib.auth.decorators import user_passes_test

@staff_member_required
def delete_attraction(request, id):

    attraction = get_object_or_404(Attraction, id=id)

    destination_slug = attraction.destination.slug

    attraction.delete()

    messages.success(request, "🗑️ Attraction deleted successfully")

    return redirect("destination_detail", slug=destination_slug)

# destinations/views.py
from django.http import JsonResponse
from .models import Destination

def api_destinations(request):
    """API endpoint for destination autocomplete"""
    query = request.GET.get('q', '')
    destinations = Destination.objects.all()
    
    if query:
        destinations = destinations.filter(name__icontains=query)
    
    data = [{
        'id': d.id,
        'name': d.name,
        'lat': d.latitude,
        'lng': d.longitude,
        'state': d.state,
        'country': d.country
    } for d in destinations[:20]]
    
    return JsonResponse(data, safe=False)


from django.http import JsonResponse
from .models import Destination

def destination_coords(request, dest_id):
    try:
        dest = Destination.objects.get(id=dest_id)
        return JsonResponse({
            'lat': dest.latitude,
            'lng': dest.longitude,
            'name': dest.name
        })
    except Destination.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)



from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Attraction
from .forms import AttractionForm


def edit_attraction(request, id):

    attraction = get_object_or_404(Attraction, id=id)

    if request.method == "POST":
        form = AttractionForm(request.POST, request.FILES, instance=attraction)  # ✅ FIXED

        if form.is_valid():
            form.save()
            messages.success(request, "✏️ Attraction updated successfully")
            return redirect("attraction_detail", id=attraction.id)

    else:
        form = AttractionForm(instance=attraction)

    return render(request, "destinations/edit_attraction.html", {
        "form": form,
        "attraction": attraction
    })

def attraction_detail(request, id):

    attraction = get_object_or_404(Attraction, id=id)

    return render(request, "destinations/attraction_detail.html", {
        "attraction": attraction
    })