from pathlib import Path

import pytest
from django.utils import timezone

from photonix.photos.models import Task

from .factories import LibraryFactory

# pytestmark = pytest.mark.django_db


from unittest.mock import patch



from photonix.photos.tasks import process_raw_task, generate_thumbnails_task, classify_photo_task

def test_tasks_created_updated(db):
    from photonix.photos.utils.db import record_photo
    snow_path = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    library = LibraryFactory()
    with patch('photonix.photos.utils.db.chain') as mock_chain:
        photo = record_photo(snow_path, library)
        mock_chain.assert_called_once_with(
            process_raw_task.s(photo_id=photo.id),
            generate_thumbnails_task.s(),
            classify_photo_task.s()
        )
