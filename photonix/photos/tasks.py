import os
import shutil
from pathlib import Path

from celery import shared_task, group
from django.conf import settings

from photonix.classifiers.color import run_on_photo as run_color
from photonix.classifiers.event import run_on_photo as run_event
from photonix.classifiers.face import run_on_photo as run_face
from photonix.classifiers.location import run_on_photo as run_location
from photonix.classifiers.object import run_on_photo as run_object
from photonix.classifiers.style import run_on_photo as run_style
from photonix.photos.models import Photo
from photonix.photos.utils.metadata import get_dimensions
from photonix.photos.utils.raw import NON_RAW_MIMETYPES, generate_jpeg
from photonix.photos.utils.thumbnails import generate_thumbnails_for_photo
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


@shared_task
def generate_thumbnails_task(photo_id):
    logger.info(f'Generating thumbnails for photo {photo_id}')
    generate_thumbnails_for_photo(photo_id)

    # Trigger classification tasks
    try:
        photo = Photo.objects.get(id=photo_id)
        library = photo.library

        tasks = []
        if library.classification_color_enabled:
            tasks.append(classify_color_task.s(photo_id))

        if library.classification_event_enabled:
            tasks.append(classify_event_task.s(photo_id))

        if library.classification_face_enabled:
            tasks.append(classify_face_task.s(photo_id))

        if library.classification_location_enabled:
            tasks.append(classify_location_task.s(photo_id))

        if library.classification_object_enabled:
            tasks.append(classify_object_task.s(photo_id))

        if library.classification_style_enabled:
            tasks.append(classify_style_task.s(photo_id))

        if tasks:
            group(tasks).apply_async()

    except Photo.DoesNotExist:
        logger.error(f'Photo {photo_id} not found during classification dispatch')


@shared_task
def classify_color_task(photo_id):
    logger.info(f'Running color classification for photo {photo_id}')
    run_color(photo_id)


@shared_task
def classify_event_task(photo_id):
    logger.info(f'Running event classification for photo {photo_id}')
    run_event(photo_id)


@shared_task
def classify_face_task(photo_id):
    logger.info(f'Running face classification for photo {photo_id}')
    run_face(photo_id)


@shared_task
def classify_location_task(photo_id):
    logger.info(f'Running location classification for photo {photo_id}')
    run_location(photo_id)


@shared_task
def classify_object_task(photo_id):
    logger.info(f'Running object classification for photo {photo_id}')
    run_object(photo_id)


@shared_task
def classify_style_task(photo_id):
    logger.info(f'Running style classification for photo {photo_id}')
    run_style(photo_id)
