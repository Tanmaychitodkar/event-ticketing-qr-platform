from django.contrib import admin
from django.urls import path

from users.views import (
    register_view,
    login_view,
    logout_view,
)

from events.views import (
    homepage,
    events_page,
    event_detail,
    ticket_availability,
    add_to_cart,
    cart_view,
    checkout_view,
    process_payment,
    my_tickets_view,
    validate_ticket,
    ticket_scanner,
    organizer_dashboard
)


urlpatterns = [

    # ============================================================
    # ADMIN
    # ============================================================

    path(
        "admin/",
        admin.site.urls
    ),


    # ============================================================
    # HOMEPAGE
    # ============================================================

    path(
        "",
        homepage,
        name="homepage"
    ),

    path(
        "homepage/",
        homepage,
        name="homepage"
    ),


    # ============================================================
    # EVENTS
    # ============================================================

    path(
        "events/",
        events_page,
        name="events"
    ),

    path(
        "events/<int:event_id>/",
        event_detail,
        name="event_detail"
    ),

    # Live ticket availability
    path(
        "events/<int:event_id>/availability/",
        ticket_availability,
        name="ticket_availability"
    ),


    # ============================================================
    # CART
    # ============================================================

    path(
        "cart/add/<int:ticket_type_id>/",
        add_to_cart,
        name="add_to_cart"
    ),

    path(
        "cart/",
        cart_view,
        name="cart"
    ),


    # ============================================================
    # CHECKOUT
    # ============================================================

    path(
        "checkout/",
        checkout_view,
        name="checkout"
    ),

    path(
        "checkout/payment/",
        process_payment,
        name="process_payment"
    ),


    # ============================================================
    # MY TICKETS
    # ============================================================

    path(
        "my-tickets/",
        my_tickets_view,
        name="my_tickets"
    ),
    
    
    
# ============================================================
# V4 — QR VALIDATION
# ============================================================

    path(
        "validate-ticket/",
        validate_ticket,
        name="validate_ticket"
   ),
    
   #organizer dashboard---------
   
   path(
    "organizer/",
    organizer_dashboard,
    name="organizer_dashboard"
), 
# ============================================================
# V4 — STAFF SCANNER PAGE
# ============================================================

    path(
        "ticket-scanner/",
        ticket_scanner,
        name="ticket_scanner"
    ),


    # ============================================================
    # AUTHENTICATION
    # ============================================================

    path(
        "register/",
        register_view,
        name="register"
    ),

    path(
        "login/",
        login_view,
        name="login"
    ),

    path(
        "logout/",
        logout_view,
        name="logout"
    ),
]