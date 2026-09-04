from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid


# ============================================================
# V1 — VENUE
# ============================================================

class Venue(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField()

    def __str__(self):
        return self.name


# ============================================================
# V1 — EVENT
# ============================================================

class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE
    )

    date = models.DateField()
    time = models.TimeField()

    # Maximum number of tickets allocated for this event
    ticket_allocation = models.PositiveIntegerField()

    def clean(self):
        if self.venue and self.ticket_allocation > self.venue.capacity:
            raise ValidationError(
                "Ticket allocation cannot exceed the venue capacity."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ============================================================
# V2 — DYNAMIC TICKET TYPES
# ============================================================

class TicketType(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="ticket_types"
    )

    # Examples:
    # VIP
    # General Admission
    # Early Bird
    name = models.CharField(max_length=100)

    # Price of one ticket
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Maximum number available for this ticket type
    quantity = models.PositiveIntegerField()

    def clean(self):
        if self.event:
            existing_quantity = (
                TicketType.objects
                .filter(event=self.event)
                .exclude(pk=self.pk)
                .aggregate(total=models.Sum("quantity"))["total"] or 0
            )

            if existing_quantity + self.quantity > self.event.ticket_allocation:
                raise ValidationError(
                    "Total ticket quantity cannot exceed the event allocation."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event.name} - {self.name}"


# ============================================================
# V2 — CART
# ============================================================

class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # Cart remains active for 10 minutes
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        # Automatically give a new cart a 10-minute lifetime.
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)

        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Cart #{self.id} - {self.user.username}"


# ============================================================
# V2 — CART ITEM / TICKET LOCK
# ============================================================

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )

    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.CASCADE
    )

    # Number of tickets temporarily held
    quantity = models.PositiveIntegerField()

    def clean(self):
        # Quantity must be greater than zero
        if self.quantity <= 0:
            raise ValidationError(
                "Cart quantity must be greater than zero."
            )

        # Expired cart cannot hold tickets
        if self.cart.is_expired():
            raise ValidationError(
                "This cart has expired. Please create a new cart."
            )

        # Count tickets held by OTHER active carts
        locked_quantity = (
            CartItem.objects
            .filter(
                ticket_type=self.ticket_type,
                cart__expires_at__gt=timezone.now()
            )
            .exclude(cart=self.cart)
            .aggregate(total=models.Sum("quantity"))["total"] or 0
        )

        # Check ticket availability
        if locked_quantity + self.quantity > self.ticket_type.quantity:
            raise ValidationError(
                "Not enough tickets available. "
                "Some tickets are currently locked by another cart."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_type.name} - {self.quantity}"


# ============================================================
# V3 — PURCHASE
# ============================================================

class Purchase(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Successful"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="purchases"
    )

    # IMPORTANT:
    # A cart is temporary and can be deleted after payment.
    # Therefore the Purchase must NOT be deleted when the Cart
    # is deleted.
    cart = models.OneToOneField(
        Cart,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    purchased_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Purchase #{self.id} - {self.user.username}"


# ============================================================
# V3 — TICKET
# ============================================================

class Ticket(models.Model):

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    # Unique value stored for the ticket.
    # This value can be used as QR-code data.
    qr_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    # ========================================================
    # V4 — QR CHECK-IN
    # ========================================================

    checked_in = models.BooleanField(
        default=False
    )

    checked_in_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    
    
    

    def __str__(self):
        return f"{self.ticket_type.name} - {self.qr_code}"