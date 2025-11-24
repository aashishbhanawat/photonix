from django.contrib.auth.models import AbstractUser
from django.db import models

from photonix.common.models import UUIDModel, VersionedModel


class User(UUIDModel, AbstractUser):
    has_set_personal_info = models.BooleanField(
        default=False, help_text='User has set their personal info')
    has_created_library = models.BooleanField(
        default=False, help_text='User has created a library')
    has_configured_importing = models.BooleanField(
        default=False, help_text='User has configured photo importing')
    has_configured_image_analysis = models.BooleanField(
        default=False, help_text='User has configured image analysis')
