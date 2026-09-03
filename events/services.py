from django.db import transaction
from django.utils import timezone

from .models import Purchase, Ticket


@transaction.atomic
def complete_purchase(cart):
    """
    Complete a cart purchase.

    Only active carts can be purchased.
    A successful purchase creates one Ticket
    for each ticket in the cart.
    """

    if cart.is_expired():
        raise ValueError(
            "This cart has expired. Please create a new cart."
        )

    # Prevent the same cart from being purchased twice.
    if hasattr(cart, "purchase"):
        if cart.purchase.status == Purchase.Status.SUCCESS:
            raise ValueError(
                "This cart has already been purchased."
            )

    purchase = Purchase.objects.create(
        user=cart.user,
        cart=cart,
        status=Purchase.Status.SUCCESS,
        purchased_at=timezone.now(),
    )

    for item in cart.items.select_related("ticket_type"):
        for _ in range(item.quantity):
            Ticket.objects.create(
                purchase=purchase,
                user=cart.user,
                ticket_type=item.ticket_type,
            )

    return purchase