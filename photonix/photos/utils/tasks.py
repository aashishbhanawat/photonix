from django.utils import timezone
from datetime import timedelta
from photonix.web.utils import logger
from photonix.photos.models import Photo, PhotoFile
from photonix.photos.utils.thumbnails import THUMBNAILER_VERSION
from photonix.photos.utils.raw import NON_RAW_MIMETYPES
from photonix.photos import tasks


def requeue_stuck_tasks(task_type, age_hours=24, max_num=8):
    logger.info(f'Requeuing stuck tasks of type {task_type}')
    cutoff = timezone.now() - timedelta(hours=age_hours)
    requeued_count = 0

    if task_type == 'generate_thumbnails':
        photos = Photo.objects.filter(
            thumbnailed_version__lt=THUMBNAILER_VERSION,
            updated_at__lt=cutoff
        )[:max_num]
        for photo in photos:
            tasks.generate_thumbnails_task.delay(photo.id)
            requeued_count += 1

    elif task_type == 'process_raw':
        photo_files = PhotoFile.objects.filter(
            raw_processed=False,
            updated_at__lt=cutoff
        ).exclude(mimetype__in=NON_RAW_MIMETYPES)[:max_num]
        for pf in photo_files:
            tasks.process_raw_task.delay(pf.photo_id)
            requeued_count += 1

    elif task_type.startswith('classify.'):
        classifier_type = task_type.split('.')[1]
        type_map = {
            'color': ('C', tasks.classify_color_task),
            'location': ('L', tasks.classify_location_task),
            'object': ('O', tasks.classify_object_task),
            'style': ('S', tasks.classify_style_task),
            'face': ('F', tasks.classify_face_task),
            'event': ('E', tasks.classify_event_task),
        }
        if classifier_type in type_map:
            tag_type, task_func = type_map[classifier_type]
            photos = Photo.objects.filter(
                thumbnailed_version=THUMBNAILER_VERSION,
                updated_at__lt=cutoff
            ).exclude(photo_tags__tag__type=tag_type)[:max_num]
            for photo in photos:
                task_func.delay(photo.id)
                requeued_count += 1

    return requeued_count


def count_remaining_task(task_type):
    """Returned count of remaining task."""
    remaining = 0
    total = 0

    if task_type == 'generate_thumbnails':
        total = Photo.objects.count()
        remaining = Photo.objects.filter(thumbnailed_version__lt=THUMBNAILER_VERSION).count()

    elif task_type == 'process_raw':
        raw_files = PhotoFile.objects.exclude(mimetype__in=NON_RAW_MIMETYPES)
        total = raw_files.count()
        remaining = raw_files.filter(raw_processed=False).count()

    elif task_type.startswith('classify.'):
        classifier_type = task_type.split('.')[1]
        type_map = {
            'color': 'C',
            'location': 'L',
            'object': 'O',
            'style': 'S',
            'face': 'F',
            'event': 'E',
        }
        tag_type = type_map.get(classifier_type)
        if tag_type:
            # We assume a photo needs classification if it's thumbnailed but has no tags of that type.
            # This is an approximation as some photos might genuinely have no results for some classifiers.
            photos_ready = Photo.objects.filter(thumbnailed_version=THUMBNAILER_VERSION)
            total = photos_ready.count()
            remaining = photos_ready.exclude(photo_tags__tag__type=tag_type).count()

    return {'remaining': remaining, 'total': total}
