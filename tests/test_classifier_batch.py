import queue
import threading
import uuid
from datetime import datetime
from pathlib import Path
from time import time

import factory
import pytest
from mock import patch

from photonix.classifiers.color import ColorModel, run_on_photo
from photonix.classifiers.style import StyleModel, run_on_photo
from photonix.photos.utils.classification import ThreadedQueueProcessor

from .factories import (LibraryFactory, PhotoFactory, PhotoFileFactory,
                        TaskFactory)


@pytest.mark.django_db
@patch('photonix.classifiers.style.model.StyleModel.load_labels')
@patch('photonix.classifiers.style.model.StyleModel.load_graph')
@patch('photonix.classifiers.style.model.StyleModel.predict')
@patch('photonix.classifiers.style.model.StyleModel.ensure_downloaded')
def test_classifier_batch(mock_ensure_downloaded, mock_predict, mock_load_graph, mock_load_labels):
    mock_ensure_downloaded.return_value = True
    mock_predict.return_value = [('serene', 0.99)]
    mock_load_graph.return_value = None
    mock_load_labels.return_value = []
    model = StyleModel()
    photo = PhotoFactory()
    PhotoFileFactory(photo=photo)

    for _ in range(4):
        TaskFactory(subject_id=photo.id)

    start = time()

    threaded_queue_processor = ThreadedQueueProcessor(
        model, 'classify.style', run_on_photo, 1, 64)
    threaded_queue_processor.run(loop=False)

    assert time() - start > 0
    assert time() - start < 100
    assert photo.photo_tags.count() == 1
    assert photo.photo_tags.all()[0].tag.name == 'serene'
    assert photo.photo_tags.all()[0].confidence > 0.9
