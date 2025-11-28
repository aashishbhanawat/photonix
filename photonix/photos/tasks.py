import os
import shutil
from pathlib import Path

from celery import shared_task
from django.conf import settings

from photonix.photos.models import Photo, Task
from photonix.photos.utils.metadata import get_dimensions
from photonix.photos.utils.raw import NON_RAW_MIMETYPES, generate_jpeg
from photonix.web.utils import logger


@shared_task
def process_raw_task(photo_id):
    logger.info(f'Processing raw photos for photo {photo_id}')
    try:
        photo = Photo.objects.get(id=photo_id)
    except Photo.DoesNotExist:
        logger.error(f'Photo {photo_id} not found')
        return

    for photo_file in photo.files.all():
        # TODO: Make raw photo detection better
        if photo_file.mimetype not in NON_RAW_MIMETYPES:
            logger.info(f'Processing raw file {photo_file.id}')
            output_path, version, process_params, external_version = generate_jpeg(
                photo_file.path)

            if not output_path:
                logger.error(f'Could not generate JPEG for {photo_file.path}')
                continue

            if not os.path.isdir(settings.PHOTO_RAW_PROCESSED_DIR):
                os.makedirs(settings.PHOTO_RAW_PROCESSED_DIR)
            destination_path = Path(settings.PHOTO_RAW_PROCESSED_DIR) / \
                str('{}.jpg'.format(photo_file.id))
            shutil.move(output_path, str(destination_path))

            photo_file.raw_processed = True
            photo_file.raw_version = version
            photo_file.raw_external_params = process_params
            photo_file.raw_external_version = external_version

            if not photo_file.width or not photo_file.height:
                width, height = get_dimensions(photo_file.base_image_path)
                photo_file.width = width
                photo_file.height = height

            photo_file.save()
            logger.info(f'Processed raw file {photo_file.id}')

    # Trigger next step
    # TODO: Remove this legacy task creation when generate_thumbnails is migrated to Celery (Task 1.3)
    Task.objects.create(
        type='generate_thumbnails',
        subject_id=photo.id,
        library=photo.library
    )
