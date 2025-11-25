from celery import shared_task
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from PIL import Image

from photonix.photos.models import Photo, PhotoFile
from photonix.web.utils import logger

from .utils.metadata import get_dimensions
from .utils.raw import generate_jpeg, NON_RAW_MIMETYPES

from .utils.thumbnails import generate_thumbnails_for_photo
from .utils.classification import CLASSIFIERS
from celery import group

# Import classifier runners
from photonix.classifiers import color as color_classifier
from photonix.classifiers import event as event_classifier
from photonix.classifiers import location as location_classifier
from photonix.classifiers import face as face_classifier
from photonix.classifiers import style as style_classifier
from photonix.classifiers import object as object_classifier

@shared_task
def generate_thumbnails_task(previous_task_result):
    photo_id = previous_task_result
    generate_thumbnails_for_photo(photo_id)
    return photo_id

@shared_task
def classify_color_task(photo_id):
    color_classifier.run_on_photo(photo_id)

@shared_task
def classify_event_task(photo_id):
    event_classifier.run_on_photo(photo_id)

@shared_task
def classify_location_task(photo_id):
    location_classifier.run_on_photo(photo_id)

@shared_task
def classify_face_task(photo_id):
    face_classifier.run_on_photo(photo_id)

@shared_task
def classify_style_task(photo_id):
    style_classifier.run_on_photo(photo_id)

@shared_task
def classify_object_task(photo_id):
    object_classifier.run_on_photo(photo_id)

@shared_task
def classify_photo_task(previous_task_result):
    photo_id = previous_task_result

    classifier_tasks = {
        'color': classify_color_task,
        'event': classify_event_task,
        'location': classify_location_task,
        'face': classify_face_task,
        'style': classify_style_task,
        'object': classify_object_task,
    }

    # Get enabled classifiers for the photo's library
    photo = Photo.objects.get(id=photo_id)
    enabled_classifiers = []
    for classifier in CLASSIFIERS:
        if getattr(photo.library, f'classification_{classifier}_enabled'):
            enabled_classifiers.append(classifier_tasks[classifier].s(photo_id))

    # Run enabled classifiers in parallel
    group(enabled_classifiers).apply_async()


@shared_task
def process_raw_task(photo_id):
    photo = Photo.objects.get(id=photo_id)
    for photo_file in photo.files.all():
        if photo_file.mimetype not in NON_RAW_MIMETYPES:
            output_path, version, process_params, external_version = generate_jpeg(
                photo_file.path)

            if not output_path:
                raise Exception(f'Could not generate JPEG for {photo_file.path}')

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
    return photo_id
