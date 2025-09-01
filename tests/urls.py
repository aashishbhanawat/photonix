from django.urls import re_path
from photonix.web.urls import urlpatterns as main_urlpatterns
from photonix.photos.views import dummy_thumbnail_response

urlpatterns = main_urlpatterns + [
    re_path(r'^thumbnails/(?P<path>.*)', dummy_thumbnail_response, name='dummy_thumbnail'),
]
