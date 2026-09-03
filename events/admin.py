from django.contrib import admin

from .models import (
    Venue,
    Event,
    TicketType,
    Cart,
    CartItem,
    Purchase,
    Ticket,
)


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "address",
        "capacity",
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "venue",
        "date",
        "time",
        "ticket_allocation",
    )


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event",
        "price",
        "quantity",
    )


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "created_at",
        "expires_at",
    )

    readonly_fields = (
        "created_at",
        "expires_at",
    )


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "cart",
        "ticket_type",
        "quantity",
    )


# ============================================================
# V3 — PURCHASE ADMIN
# ============================================================

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "cart",
        "status",
        "purchased_at",
    )


# ============================================================
# V3 — TICKET ADMIN
# ============================================================

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "ticket_type",
        "qr_code",
        "created_at",
    )

    readonly_fields = (
        "qr_code",
        "created_at",
    )