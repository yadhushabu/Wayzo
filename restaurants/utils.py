# restaurants/utils.py

from .models import RoomBooking
from django.utils import timezone

def auto_complete_room_bookings():

    today = timezone.now().date()

    bookings = RoomBooking.objects.filter(
        status="confirmed",
        check_out__lt=today
    )

    for booking in bookings:
        booking.complete_booking()