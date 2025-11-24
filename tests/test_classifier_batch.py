from datetime import datetime
from pathlib import Path
import queue
import threading
from time import time
import uuid

import factory
import pytest

from photonix.classifiers.color import ColorModel, run_on_photo
from photonix.classifiers.style import StyleModel, run_on_photo
from photonix.photos.utils.classification import ThreadedQueueProcessor
from .factories import PhotoFactory, PhotoFileFactory, LibraryFactory, TaskFactory


from mock import patch


@pytest.mark.django_db
@patch('photonix.classifiers.style.model.StyleModel.predict')
@patch('photonix.classifiers.style.model.StyleModel.ensure_downloaded')
def test_classifier_batch(mock_ensure_downloaded, mock_predict):
    mock_ensure_downloaded.return_value = True
    mock_predict.return_value = [('serene', 0.99)]
    model = StyleModel()
    photo = PhotoFactory()
    PhotoFileFactory(photo=photo)

    for _ in range(4):
        TaskFactory(subject_id=photo.id)

    start = time()

    threaded_queue_processor = ThreadedQueueProcessor(model, 'classify.style', run_on_photo, 1, 64)
    threaded_queue_processor.run(loop=False)

    assert time() - start > 0
    assert time() - start < 100
    assert photo.photo_tags.count() == 1
    assert photo.photo_tags.all()[0].tag.name == 'serene'
    assert photo.photo_tags.all()[0].confidence > 0.9
