from restaurants.models import RestaurantProfile

for r in RestaurantProfile.objects.all():
    if r.property_type in ["Hotel", "Resort", "Homestay"]:
        r.category = "stay"
    elif r.property_type == "Cafe":
        r.category = "cafe"
    else:
        r.category = "restaurant"

    if r.price_range and "low" in r.price_range.lower():
        r.price_level = 1
    elif r.price_range and "luxury" in r.price_range.lower():
        r.price_level = 3
    else:
        r.price_level = 2

    if not r.rating:
        r.rating = 4.0

    r.save()

print(" Data fully updated")