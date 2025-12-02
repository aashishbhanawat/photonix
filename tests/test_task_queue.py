from pathlib import Path

import pytest
from django.utils import timezone

from photonix.photos.models import Task
from photonix.photos.utils.classification import process_classify_images_tasks
from .factories import LibraryFactory

# pytestmark = pytest.mark.django_db


@pytest.fixture
def photo_fixture_snow(db):
    from photonix.photos.utils.db import record_photo
    snow_path = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    library = LibraryFactory()
    return record_photo(snow_path, library)


def test_tasks_created_updated(photo_fixture_snow):
    # After record_photo (with eager celery), generate_thumbnails task is executed immediately via Celery.
    # It should create the next task for classification.

    # Check next task has been added to classify images
    task = Task.objects.get(type='classify_images',
                            subject_id=photo_fixture_snow.id)
    assert task.status == 'P'
    assert (timezone.now() - task.created_at).seconds < 1
    assert (timezone.now() - task.updated_at).seconds < 1
    assert task.started_at == None
    assert task.finished_at == None

    # Test manually starting makes intended changes
    task.start()
    assert task.status == 'S'
    assert (timezone.now() - task.started_at).seconds < 1

    # Undo last changes
    task.status = 'P'
    task.started_at = None
    task.save()

    # Processing the classification task should create child processes
    assert task.complete_with_children == False
    assert task.status == 'P'
    process_classify_images_tasks()
    task = Task.objects.get(type='classify_images',
                            subject_id=photo_fixture_snow.id)
    assert task.status == 'S'
    assert task.children.count() == 6
    assert task.complete_with_children == True

    # Completing all the child processes should set the parent task to completed
    for child in task.children.all():
        assert child.status == 'P'
        child.start()
        assert task.status == 'S'
        assert child.status == 'S'
        child.complete()
        assert child.status == 'C'
    assert task.status == 'C'
