import pytest
from unittest import mock
from datetime import timedelta
from django.utils import timezone
from photonix.photos.models import Photo, PhotoFile, PhotoTag, Tag
from photonix.photos.utils.tasks import count_remaining_task, requeue_stuck_tasks
from photonix.photos.utils.thumbnails import THUMBNAILER_VERSION
from tests.factories import LibraryPathFactory

@pytest.mark.django_db
class TestTaskUtils:

    def test_count_remaining_task_thumbnails(self):
        lp = LibraryPathFactory()
        library = lp.library
        Photo.objects.create(library=library, thumbnailed_version=THUMBNAILER_VERSION)
        Photo.objects.create(library=library, thumbnailed_version=0)

        result = count_remaining_task('generate_thumbnails')
        assert result['total'] == 2
        assert result['remaining'] == 1

    def test_count_remaining_task_raw(self):
        lp = LibraryPathFactory()
        library = lp.library
        photo = Photo.objects.create(library=library)

        PhotoFile.objects.create(photo=photo, path='1.jpg', mimetype='image/jpeg', bytes=10, file_modified_at=timezone.now())
        PhotoFile.objects.create(photo=photo, path='2.cr2', mimetype='image/x-canon-cr2', bytes=10, file_modified_at=timezone.now(), raw_processed=False)
        PhotoFile.objects.create(photo=photo, path='3.cr2', mimetype='image/x-canon-cr2', bytes=10, file_modified_at=timezone.now(), raw_processed=True)

        result = count_remaining_task('process_raw')
        assert result['total'] == 2
        assert result['remaining'] == 1

    def test_count_remaining_task_classify(self):
        lp = LibraryPathFactory()
        library = lp.library
        p1 = Photo.objects.create(library=library, thumbnailed_version=THUMBNAILER_VERSION)
        p2 = Photo.objects.create(library=library, thumbnailed_version=THUMBNAILER_VERSION)
        p3 = Photo.objects.create(library=library, thumbnailed_version=0) # Not ready for classification

        tag_c = Tag.objects.create(library=library, name='Red', type='C', source='C')
        PhotoTag.objects.create(photo=p1, tag=tag_c, confidence=1.0)

        result = count_remaining_task('classify.color')
        # Only p1 and p2 are ready (thumbnailed)
        assert result['total'] == 2
        # p1 has color tag, p2 does not
        assert result['remaining'] == 1

    @mock.patch('photonix.photos.tasks.generate_thumbnails_task.delay')
    def test_requeue_stuck_tasks_thumbnails(self, mock_task):
        lp = LibraryPathFactory()
        library = lp.library

        # Stuck task
        p1 = Photo.objects.create(library=library, thumbnailed_version=0)
        Photo.objects.filter(id=p1.id).update(updated_at=timezone.now() - timedelta(hours=25))

        # Recent task (not stuck)
        p2 = Photo.objects.create(library=library, thumbnailed_version=0)
        Photo.objects.filter(id=p2.id).update(updated_at=timezone.now() - timedelta(hours=1))

        # Already processed
        p3 = Photo.objects.create(library=library, thumbnailed_version=THUMBNAILER_VERSION)
        Photo.objects.filter(id=p3.id).update(updated_at=timezone.now() - timedelta(hours=25))

        count = requeue_stuck_tasks('generate_thumbnails', age_hours=24)
        assert count == 1
        mock_task.assert_called_once_with(p1.id)

    @mock.patch('photonix.photos.tasks.process_raw_task.delay')
    def test_requeue_stuck_tasks_raw(self, mock_task):
        lp = LibraryPathFactory()
        library = lp.library
        photo = Photo.objects.create(library=library)

        # Stuck raw file
        pf1 = PhotoFile.objects.create(photo=photo, path='1.cr2', mimetype='image/x-canon-cr2', bytes=10, file_modified_at=timezone.now(), raw_processed=False)
        PhotoFile.objects.filter(id=pf1.id).update(updated_at=timezone.now() - timedelta(hours=25))

        # Recent raw file
        pf2 = PhotoFile.objects.create(photo=photo, path='2.cr2', mimetype='image/x-canon-cr2', bytes=10, file_modified_at=timezone.now(), raw_processed=False)
        PhotoFile.objects.filter(id=pf2.id).update(updated_at=timezone.now() - timedelta(hours=1))

        count = requeue_stuck_tasks('process_raw', age_hours=24)
        assert count == 1
        mock_task.assert_called_once_with(photo.id)

    @mock.patch('photonix.photos.tasks.classify_color_task.delay')
    def test_requeue_stuck_tasks_classify(self, mock_task):
        lp = LibraryPathFactory()
        library = lp.library

        # Stuck classification
        p1 = Photo.objects.create(library=library, thumbnailed_version=THUMBNAILER_VERSION)
        Photo.objects.filter(id=p1.id).update(updated_at=timezone.now() - timedelta(hours=25))

        # Recent classification
        p2 = Photo.objects.create(library=library, thumbnailed_version=THUMBNAILER_VERSION)
        Photo.objects.filter(id=p2.id).update(updated_at=timezone.now() - timedelta(hours=1))

        count = requeue_stuck_tasks('classify.color', age_hours=24)
        assert count == 1
        mock_task.assert_called_once_with(p1.id)

    @mock.patch('photonix.photos.tasks.generate_thumbnails_task.delay')
    def test_requeue_stuck_tasks_max_num(self, mock_task):
        lp = LibraryPathFactory()
        library = lp.library

        for i in range(10):
            p = Photo.objects.create(library=library, thumbnailed_version=0)
            Photo.objects.filter(id=p.id).update(updated_at=timezone.now() - timedelta(hours=25))

        count = requeue_stuck_tasks('generate_thumbnails', max_num=5)
        assert count == 5
        assert mock_task.call_count == 5
