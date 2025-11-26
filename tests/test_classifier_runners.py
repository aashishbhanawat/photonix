from pathlib import Path
from unittest import mock

import pytest

from .factories import LibraryFactory

# pytestmark = pytest.mark.django_db


@pytest.fixture
def photo_fixture_snow(db):
    from photonix.photos.utils.db import record_photo
    snow_path = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    library = LibraryFactory()
    return record_photo(snow_path, library)


@pytest.fixture
def photo_fixture_tree(db):
    from photonix.photos.utils.db import record_photo
    tree_path = str(Path(__file__).parent / 'photos' / 'tree.jpg')
    library = LibraryFactory()
    return record_photo(tree_path, library)


def test_color_via_runner(photo_fixture_snow):
    from photonix.classifiers.color.model import run_on_photo

    # Path on it's own returns a None Photo object along with the result
    snow = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    photo, result = run_on_photo(snow)

    assert photo is None
    assert len(result) == 13
    assert result[0][0] == 'Red'
    assert '{0:.3f}'.format(result[0][1]) == '0.163'

    # Passing in a Photo object should tag the object
    run_on_photo(photo_fixture_snow.id)
    assert photo_fixture_snow.photo_tags.count() >= 13
    assert photo_fixture_snow.photo_tags.all()[0].tag.name == 'Red'
    assert photo_fixture_snow.photo_tags.all()[0].tag.type == 'C'
    assert '{0:.3f}'.format(photo_fixture_snow.photo_tags.all()[
                            0].significance) == '0.163'


def test_location_via_runner(photo_fixture_tree):
    from photonix.classifiers.location.model import run_on_photo

    # Path on it's own returns a None Photo object along with the result
    snow = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    photo, result = run_on_photo(snow)

    # This photo has no GPS coordinates
    assert photo is None
    assert result['city'] is None
    assert result['country'] is None

    # Path which does have GPS coordinates
    tree = str(Path(__file__).parent / 'photos' / 'tree.jpg')
    photo, result = run_on_photo(tree)
    assert result['country']['name'] == 'Greece'
    assert result['country']['code'] == 'GR'
    assert result['city']['name'] == 'Firá'
    assert result['city']['country_name'] == 'Greece'

    # Photo object with location to tag should have tags for country and city
    photo, result = run_on_photo(photo_fixture_tree.id)
    assert photo_fixture_tree.photo_tags.all().count() >= 2
    assert photo_fixture_tree.photo_tags.all()[0].tag.name == 'Greece'
    assert photo.photo_tags.all()[0].confidence == 1.0
    assert photo.photo_tags.all()[0].significance == 1.0
    assert photo.photo_tags.all()[1].tag.name == 'Firá'
    assert photo.photo_tags.all()[1].confidence == 0.5
    assert photo.photo_tags.all()[1].significance == 0.5
    assert photo.photo_tags.all()[1].tag.parent.name == 'Greece'


@pytest.fixture
def photo_fixture_object(db):
    from photonix.photos.utils.db import record_photo
    object_path = str(Path(__file__).parent / 'photos' / 'object.jpg')
    library = LibraryFactory(classification_color_enabled=False)
    return record_photo(object_path, library)


@mock.patch('photonix.classifiers.object.model.ObjectModel.predict')
def test_object_via_runner(mock_predict, photo_fixture_object):
    from photonix.classifiers.object.model import run_on_photo
    mock_predict.return_value = [{'label': 'Tree', 'score': 0.602, 'significance': 0.134, 'x': 0.787, 'y': 0.374, 'width': 0.340, 'height': 0.655}, {'label': 'Tree', 'score': 0.525,
                                                                                                                                                     'significance': 0.016, 'x': 0.1, 'y': 0.2, 'width': 0.3, 'height': 0.4}, {'label': 'Tree', 'score': 0.453, 'significance': 0.025, 'x': 0.5, 'y': 0.6, 'width': 0.7, 'height': 0.8}]

    # Path on it's own returns a None Photo object along with the result
    snow = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    photo, result = run_on_photo(snow)

    assert photo is None
    assert len(result) == 3
    assert result[0]['label'] == 'Tree'
    assert '{0:.3f}'.format(result[0]['significance']) == '0.134'

    # Passing in a Photo object should tag the object
    run_on_photo(photo_fixture_object.id)
    assert photo_fixture_object.photo_tags.count() >= 3
    assert photo_fixture_object.photo_tags.all()[0].tag.name == 'Tree'
    assert photo_fixture_object.photo_tags.all()[0].tag.type == 'O'
    assert '{0:.3f}'.format(photo_fixture_object.photo_tags.all()[
                            0].significance) == '0.134'


@mock.patch('photonix.classifiers.style.model.StyleModel.predict')
def test_style_via_runner(mock_predict, photo_fixture_snow):
    from photonix.classifiers.style.model import run_on_photo

    # Set up mock return value
    mock_predict.return_value = [('serene', 0.962)]

    # Path on it's own returns a None Photo object along with the result
    snow = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    photo, result = run_on_photo(snow)

    assert photo is None
    assert len(result) == 1
    assert result[0][0] == 'serene'
    assert '{0:.3f}'.format(result[0][1]) == '0.962'

    # Passing in a Photo object should tag the object
    run_on_photo(photo_fixture_snow.id)
    assert photo_fixture_snow.photo_tags.count() >= 1
    assert photo_fixture_snow.photo_tags.all()[0].tag.name == 'serene'
    assert photo_fixture_snow.photo_tags.all()[0].tag.type == 'S'
    assert '{0:.3f}'.format(photo_fixture_snow.photo_tags.all()[
                            0].significance) == '0.962'
