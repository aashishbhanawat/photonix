import os
import shutil

from celery import shared_task
from django.conf import settings
from pathlib import Path

from photonix.photos.models import PhotoFile
from photonix.photos.utils.raw import generate_jpeg
from photonix.photos.utils.metadata import get_dimensions
from photonix.web.utils import logger


@shared_task
def add(x, y):
    return x + y


@shared_task
def hello_world():
    print("Hello from a Celery task!")
    return "Hello, World!"


@shared_task
def process_raw_task(photo_file_id):
    """
    Celery task to process a RAW photo file and generate a JPEG preview.
    """
    try:
        photo_file = PhotoFile.objects.get(id=photo_file_id)
    except PhotoFile.DoesNotExist:
        logger.error(f"PhotoFile with id {photo_file_id} not found.")
        return

    logger.info(f"Starting RAW processing for PhotoFile {photo_file.id} at path {photo_file.path}")

    output_path, version, process_params, external_version = generate_jpeg(photo_file.path)

    if not output_path:
        # The generate_jpeg function already logs the error.
        return

    if not os.path.isdir(settings.PHOTO_RAW_PROCESSED_DIR):
        os.mkdir(settings.PHOTO_RAW_PROCESSED_DIR)

    destination_path = Path(settings.PHOTO_RAW_PROCESSED_DIR) / f'{photo_file.id}.jpg'
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

    logger.info(f"Finished RAW processing for PhotoFile {photo_file.id}. JPEG saved to {destination_path}")

    # TODO: Trigger the next task in the pipeline (thumbnailing)
    # This will be implemented in Task 1.3
    # from .tasks import generate_thumbnails_task
    # generate_thumbnails_task.delay(photo_file.photo.id)
