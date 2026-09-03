from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        ORGANIZER = "ORGANIZER", "Organizer"
        ATTENDEE = "ATTENDEE", "Attendee"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ATTENDEE,
    )