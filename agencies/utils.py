from django.utils import timezone
from .models import PackageBooking
from community.models import Notification

def auto_cancel_expired_bookings():

    expired_bookings = PackageBooking.objects.filter(
        status="pending",
        approval_deadline__lt=timezone.now()
    )

    for booking in expired_bookings:

        booking.status = "cancelled"
        booking.cancelled_by = "system"

        refund_amount = booking.calculate_refund_amount()

        booking.refund_amount = refund_amount
        booking.refund_percentage = 100
        booking.is_refunded = True

        booking.save()

        # Notify traveller
        Notification.objects.create(
            user=booking.traveller,
            notification_type="booking",
            message=(
                f"Your booking for {booking.package.title} "
                f"was automatically cancelled because the agency "
                f"did not confirm within 24 hours. "
                f"Refund ₹{refund_amount}"
            )
        )

        # Notify agency
        Notification.objects.create(
            user=booking.package.agency.user,
            notification_type="booking",
            message=(
                f"Booking for {booking.package.title} "
                f"was auto-cancelled due to no response within 24 hours."
            )
        )

from django.utils import timezone
from .models import Refund


def process_refund(booking):
    refund = Refund.objects.create(
        booking=booking,
        amount=booking.refund_amount,
        status="success",  # later replace with Razorpay API response
        gateway_ref_id=f"RFND_{booking.id}_{timezone.now().timestamp()}"
    )

    booking.refund_status = "success"
    booking.refund_reference_id = refund.gateway_ref_id
    booking.refund_processed_at = timezone.now()
    booking.save()

    return refund

from reportlab.pdfgen import canvas
from io import BytesIO
from django.http import HttpResponse

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.utils import timezone


def generate_invoice_pdf(booking):

    payments = booking.payments.filter(
        is_paid=True
    ).order_by("paid_at")

    buffer = BytesIO()

    p = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4

    y = height - 50

    # =====================================
    # HEADER
    # =====================================

    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, y, "WAYZO")

    y -= 30

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "TRAVEL BOOKING INVOICE")

    y -= 20

    p.line(50, y, width - 50, y)

    y -= 40

    # =====================================
    # INVOICE DETAILS
    # =====================================

    invoice_no = (
        booking.invoice_number
        if booking.invoice_number
        else f"INV-{booking.id:06d}"
    )

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Invoice Details")

    y -= 25

    p.setFont("Helvetica", 11)

    p.drawString(
        50,
        y,
        f"Invoice Number : {invoice_no}"
    )

    y -= 20

    p.drawString(
        50,
        y,
        f"Booking ID : {booking.id}"
    )

    y -= 20

    p.drawString(
        50,
        y,
        f"Booked On : {booking.booked_at.strftime('%d-%m-%Y %H:%M')}"
    )

    y -= 20

    p.drawString(
        50,
        y,
        f"Travel Date : {booking.travel_date.strftime('%d-%m-%Y')}"
    )

    y -= 35

    # =====================================
    # TRAVELLER DETAILS
    # =====================================

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Traveller Details")

    y -= 25

    p.setFont("Helvetica", 11)

    p.drawString(
        50,
        y,
        f"Name : {booking.traveller.get_full_name() or booking.traveller.username}"
    )

    y -= 20

    p.drawString(
        50,
        y,
        f"Email : {booking.traveller.email}"
    )

    y -= 20

    p.drawString(
        50,
        y,
        f"Travellers Count : {booking.travellers_count}"
    )

    y -= 35

    # =====================================
    # PACKAGE DETAILS
    # =====================================

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Package Details")

    y -= 25

    p.setFont("Helvetica", 11)

    p.drawString(
        50,
        y,
        f"Package : {booking.package.title}"
    )

    y -= 20

    p.drawString(
        50,
        y,
        f"Agency : {booking.package.agency.agency_name}"
    )

    y -= 35

    # =====================================
    # BOOKING STATUS
    # =====================================

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Booking Information")

    y -= 25

    p.setFont("Helvetica", 11)

    p.drawString(
        50,
        y,
        f"Booking Status : {booking.get_status_display()}"
    )

    y -= 20

    p.drawString(
        50,
        y,
        f"Payment Status : {booking.get_payment_status_display()}"
    )

    y -= 35

    # =====================================
    # PAYMENT SUMMARY
    # =====================================

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Payment Summary")

    y -= 25

    p.setFont("Helvetica", 11)

    p.drawString(
        50,
        y,
        f"Total Amount : ₹{booking.total_amount}"
    )

    y -= 20

    p.drawString(
        50,
        y,
        f"Advance Amount : ₹{booking.advance_amount}"
    )

    y -= 20

    p.drawString(
        50,
        y,
        f"Remaining Amount : ₹{booking.remaining_amount}"
    )

    y -= 35

    # =====================================
    # PAYMENT HISTORY
    # =====================================

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Payment History")

    y -= 25

    if payments.exists():

        p.setFont("Helvetica", 10)

        for payment in payments:

            p.drawString(
                50,
                y,
                f"Payment Type : {payment.get_payment_type_display()}"
            )

            y -= 18

            p.drawString(
                70,
                y,
                f"Amount : ₹{payment.amount}"
            )

            y -= 18

            p.drawString(
                70,
                y,
                f"Transaction ID : {payment.transaction_id or 'N/A'}"
            )

            y -= 18

            if payment.paid_at:
                p.drawString(
                    70,
                    y,
                    f"Paid On : {payment.paid_at.strftime('%d-%m-%Y %H:%M')}"
                )
                y -= 18

            y -= 10

    else:

        p.setFont("Helvetica", 10)

        p.drawString(
            50,
            y,
            "No successful payments found."
        )

        y -= 25

    # =====================================
    # REFUND DETAILS
    # =====================================

    if booking.status == "cancelled":

        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Refund Details")

        y -= 25

        p.setFont("Helvetica", 11)

        p.drawString(
            50,
            y,
            f"Refund Status : {booking.refund_status}"
        )

        y -= 20

        p.drawString(
            50,
            y,
            f"Refund Amount : ₹{booking.refund_amount or 0}"
        )

        y -= 20

        p.drawString(
            50,
            y,
            f"Refunded : {'Yes' if booking.is_refunded else 'No'}"
        )

        y -= 30

    # =====================================
    # FOOTER
    # =====================================

    p.line(50, 100, width - 50, 100)

    p.setFont("Helvetica-Oblique", 10)

    p.drawString(
        50,
        80,
        "Thank you for choosing Wayzo."
    )

    p.drawString(
        50,
        65,
        "This is a computer-generated invoice and does not require a signature."
    )

    p.drawString(
        50,
        50,
        f"Generated On : {timezone.now().strftime('%d-%m-%Y %H:%M')}"
    )

    p.showPage()
    p.save()

    buffer.seek(0)

    return buffer