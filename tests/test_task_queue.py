from pathlib import Path

from django.utils import timezone
import pytest

from .factories import LibraryFactory
from photonix.photos.models import Task
from photonix.photos.utils.classification import process_classify_images_tasks
from photonix.photos.utils.thumbnails import process_generate_thumbnails_tasks

# pytestmark = pytest.mark.django_db


@pytest.fixture
def photo_fixture_snow(db):
    from photonix.photos.utils.db import record_photo
    snow_path = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    library = LibraryFactory()
    return record_photo(snow_path, library)


