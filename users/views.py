from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from .models import User


def register_view(request):
    if request.user.is_authenticated:
        return redirect("homepage")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        role = request.POST.get("role", User.Role.ATTENDEE)

        if not username or not email or not password:
            messages.error(request, "Please fill in all required fields.")

        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")

        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")

        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")

        elif role not in [User.Role.ATTENDEE, User.Role.ORGANIZER]:
            messages.error(request, "Invalid role selected.")

        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
            )

            login(request, user)
            return redirect("homepage")

    return render(request, "register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("homepage")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)
            return redirect("homepage")

        messages.error(request, "Invalid username or password.")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("homepage")