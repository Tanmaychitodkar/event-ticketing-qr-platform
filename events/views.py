from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from .models import (
    Event,
    TicketType,
    Cart,
    CartItem,
    Purchase,
    Ticket,
)


# ============================================================
# AVAILABILITY HELPER
# ============================================================

def get_ticket_availability(ticket_type, exclude_cart=None):
    """
    Calculate real-time available tickets.

    Available =
        Total tickets
        - Successfully purchased tickets
        - Tickets currently locked in other active carts
    """

    # --------------------------------------------------------
    # 1. Tickets already sold
    # --------------------------------------------------------

    sold_quantity = Ticket.objects.filter(
        ticket_type=ticket_type,
        purchase__status=Purchase.Status.SUCCESS
    ).count()


    # --------------------------------------------------------
    # 2. Tickets temporarily locked in active carts
    # --------------------------------------------------------

    locked_query = CartItem.objects.filter(
        ticket_type=ticket_type,
        cart__expires_at__gt=timezone.now()
    )


    # Don't count the current user's own cart
    if exclude_cart:

        locked_query = locked_query.exclude(
            cart=exclude_cart
        )


    locked_quantity = locked_query.aggregate(
        total=models.Sum("quantity")
    )["total"] or 0


    # --------------------------------------------------------
    # 3. Calculate remaining tickets
    # --------------------------------------------------------

    available_quantity = max(
        ticket_type.quantity
        - sold_quantity
        - locked_quantity,
        0
    )


    return available_quantity


# ============================================================
# HOMEPAGE
# ============================================================

def homepage(request):

    search_query = request.GET.get(
        "q",
        ""
    ).strip()


    events = Event.objects.select_related(
        "venue"
    ).prefetch_related(
        "ticket_types"
    ).order_by(
        "date",
        "time"
    )


    # Search
    if search_query:

        events = events.filter(
            name__icontains=search_query
        )


    # --------------------------------------------------------
    # Calculate REAL availability for every event
    # --------------------------------------------------------

    for event in events:

        total_available = 0


        for ticket_type in event.ticket_types.all():

            total_available += get_ticket_availability(
                ticket_type
            )


        event.available_quantity = total_available


    return render(
        request,
        "home.html",
        {
            "events": events,
            "search_query": search_query,
        }
    )


# ============================================================
# EVENTS PAGE
# ============================================================

def events_page(request):

    events = Event.objects.select_related(
        "venue"
    ).prefetch_related(
        "ticket_types"
    ).order_by(
        "date",
        "time"
    )


    # Calculate real availability
    for event in events:

        total_available = 0


        for ticket_type in event.ticket_types.all():

            total_available += get_ticket_availability(
                ticket_type
            )


        event.available_quantity = total_available


    return render(
        request,
        "events.html",
        {
            "events": events
        }
    )


# ============================================================
# EVENT DETAIL
# ============================================================

def event_detail(request, event_id):

    event = get_object_or_404(
        Event.objects.select_related(
            "venue"
        ),
        id=event_id
    )


    tickets = event.ticket_types.all()


    # --------------------------------------------------------
    # Get current user's cart
    # --------------------------------------------------------

    cart = None


    if request.user.is_authenticated:

        cart = Cart.objects.filter(
            user=request.user
        ).first()


        # Remove expired cart
        if cart and cart.is_expired():

            cart.delete()

            cart = None


    # --------------------------------------------------------
    # Calculate availability
    # --------------------------------------------------------

    for ticket in tickets:

        ticket.available_quantity = get_ticket_availability(
            ticket,
            exclude_cart=cart
        )


    return render(
        request,
        "event_detail.html",
        {
            "event": event,
            "tickets": tickets,
        }
    )


# ============================================================
# LIVE AVAILABILITY API
# ============================================================

def ticket_availability(request, event_id):

    event = get_object_or_404(
        Event,
        id=event_id
    )


    availability = {}


    for ticket in event.ticket_types.all():

        availability[str(ticket.id)] = (
            get_ticket_availability(ticket)
        )


    return JsonResponse(
        {
            "availability": availability
        }
    )


# ============================================================
# ADD TO CART
# ============================================================

@login_required(login_url="login")
def add_to_cart(request, ticket_type_id):

    ticket_type = get_object_or_404(
        TicketType.objects.select_related(
            "event"
        ),
        id=ticket_type_id
    )


    # --------------------------------------------------------
    # Only POST allowed
    # --------------------------------------------------------

    if request.method != "POST":

        return redirect(
            "event_detail",
            event_id=ticket_type.event.id
        )


    # --------------------------------------------------------
    # Get quantity
    # --------------------------------------------------------

    try:

        quantity = int(
            request.POST.get(
                "quantity",
                1
            )
        )

    except (TypeError, ValueError):

        quantity = 0


    # Quantity must be positive
    if quantity <= 0:

        messages.error(
            request,
            "Please select a valid quantity."
        )

        return redirect(
            "event_detail",
            event_id=ticket_type.event.id
        )


    # --------------------------------------------------------
    # Get user's cart
    # --------------------------------------------------------

    cart = Cart.objects.filter(
        user=request.user
    ).first()


    # Remove expired cart
    if cart and cart.is_expired():

        cart.delete()

        cart = None


    # Create cart if needed
    if not cart:

        cart = Cart.objects.create(
            user=request.user
        )


    # --------------------------------------------------------
    # Check existing cart item
    # --------------------------------------------------------

    cart_item = CartItem.objects.filter(
        cart=cart,
        ticket_type=ticket_type
    ).first()


    existing_quantity = (
        cart_item.quantity
        if cart_item
        else 0
    )


    # New total quantity
    new_quantity = (
        existing_quantity + quantity
    )


    # --------------------------------------------------------
    # Check real availability
    # --------------------------------------------------------

    available_for_user = get_ticket_availability(
        ticket_type,
        exclude_cart=cart
    )


    if new_quantity > available_for_user:

        messages.error(
            request,
            f"Only {available_for_user} "
            f"{ticket_type.name} ticket(s) are available."
        )

        return redirect(
            "event_detail",
            event_id=ticket_type.event.id
        )


    # --------------------------------------------------------
    # Save cart item
    # --------------------------------------------------------

    try:

        if cart_item:

            cart_item.quantity = new_quantity

            cart_item.full_clean()

            cart_item.save()

        else:

            cart_item = CartItem(
                cart=cart,
                ticket_type=ticket_type,
                quantity=new_quantity
            )

            cart_item.full_clean()

            cart_item.save()


    except ValidationError as e:

        if hasattr(
            e,
            "message_dict"
        ):

            error_messages = []


            for field_errors in e.message_dict.values():

                error_messages.extend(
                    field_errors
                )


            message = " ".join(
                error_messages
            )

        else:

            message = " ".join(
                e.messages
            )


        messages.error(
            request,
            message
        )


        return redirect(
            "event_detail",
            event_id=ticket_type.event.id
        )


    messages.success(
        request,
        f"{quantity} "
        f"{ticket_type.name} ticket(s) "
        f"added to your cart."
    )


    return redirect(
        "cart"
    )


# ============================================================
# CART
# ============================================================

@login_required(login_url="login")
def cart_view(request):

    cart = Cart.objects.filter(
        user=request.user
    ).first()


    # Remove expired cart
    if cart and cart.is_expired():

        cart.delete()

        cart = None


    items = (
        cart.items.select_related(
            "ticket_type",
            "ticket_type__event"
        )
        if cart
        else []
    )


    total = sum(
        item.ticket_type.price * item.quantity
        for item in items
    )


    return render(
        request,
        "cart.html",
        {
            "cart": cart,
            "items": items,
            "total": total,
        }
    )


# ============================================================
# CHECKOUT
# ============================================================

@login_required(login_url="login")
def checkout_view(request):

    cart = Cart.objects.filter(
        user=request.user
    ).first()


    # No cart
    if not cart:

        messages.error(
            request,
            "Your cart is empty."
        )

        return redirect(
            "cart"
        )


    # Check expiration
    if cart.is_expired():

        cart.delete()

        messages.error(
            request,
            "Your cart has expired. "
            "Please select your tickets again."
        )

        return redirect(
            "cart"
        )


    items = cart.items.select_related(
        "ticket_type",
        "ticket_type__event"
    )


    # Empty cart
    if not items.exists():

        messages.error(
            request,
            "Your cart is empty."
        )

        return redirect(
            "cart"
        )


    total = sum(
        item.ticket_type.price * item.quantity
        for item in items
    )


    return render(
        request,
        "checkout.html",
        {
            "cart": cart,
            "items": items,
            "total": total,
        }
    )


# ============================================================
# PROCESS PAYMENT
# ============================================================

@login_required(login_url="login")
def process_payment(request):

    # Payment must be POST
    if request.method != "POST":

        return redirect(
            "checkout"
        )


    # --------------------------------------------------------
    # Get cart
    # --------------------------------------------------------

    cart = Cart.objects.filter(
        user=request.user
    ).first()


    if not cart:

        messages.error(
            request,
            "Your cart is empty."
        )

        return redirect(
            "cart"
        )


    # --------------------------------------------------------
    # Check expiration
    # --------------------------------------------------------

    if cart.is_expired():

        cart.delete()

        messages.error(
            request,
            "Your cart has expired. "
            "Please select your tickets again."
        )

        return redirect(
            "cart"
        )


    # --------------------------------------------------------
    # Get cart items
    # --------------------------------------------------------

    items = list(
        cart.items.select_related(
            "ticket_type",
            "ticket_type__event"
        )
    )


    if not items:

        messages.error(
            request,
            "Your cart is empty."
        )

        return redirect(
            "cart"
        )


    try:

        # ----------------------------------------------------
        # FINAL AVAILABILITY CHECK
        # ----------------------------------------------------

        for item in items:

            available = get_ticket_availability(
                item.ticket_type,
                exclude_cart=cart
            )


            if item.quantity > available:

                messages.error(
                    request,
                    f"Only {available} "
                    f"{item.ticket_type.name} "
                    f"ticket(s) are still available."
                )

                return redirect(
                    "cart"
                )


        # ----------------------------------------------------
        # DATABASE TRANSACTION
        # ----------------------------------------------------

        with transaction.atomic():

            purchase = Purchase.objects.create(
                user=request.user,
                cart=cart,
                status=Purchase.Status.SUCCESS,
                purchased_at=timezone.now()
            )


            # ------------------------------------------------
            # Create individual tickets
            # ------------------------------------------------

            for item in items:

                for _ in range(item.quantity):

                    Ticket.objects.create(
                        purchase=purchase,
                        user=request.user,
                        ticket_type=item.ticket_type
                    )


            # ------------------------------------------------
            # Delete cart after successful payment
            # ------------------------------------------------

            cart.delete()


        messages.success(
            request,
            "Payment successful! "
            "Your tickets have been booked."
        )


        return redirect(
            "my_tickets"
        )


    except Exception as e:

        messages.error(
            request,
            f"Payment failed: {str(e)}"
        )

        return redirect(
            "checkout"
        )


# ============================================================
# MY TICKETS
# ============================================================

@login_required(login_url="login")
def my_tickets_view(request):

    tickets = Ticket.objects.filter(
        user=request.user
    ).select_related(
        "ticket_type",
        "ticket_type__event",
        "purchase"
    ).order_by(
        "-created_at"
    )


    return render(
        request,
        "my_tickets.html",
        {
            "tickets": tickets,
        }
    )