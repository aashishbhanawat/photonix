from django.urls import path, re_path

from photonix.photos.views import dummy_thumbnail_response

from .urls import urlpatterns

urlpatterns.append(
    re_path(r'thumbnails/(?P<path>[a-z0-9._\-/]+)', dummy_thumbnail_response)
)
