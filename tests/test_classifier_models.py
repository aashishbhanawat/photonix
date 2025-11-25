import os
import time
from datetime import datetime
from pathlib import Path
from unittest import mock

import fakeredis
import pytest
from django.conf import settings
from PIL import Image


@pytest.fixture(autouse=True)
def mock_redis():
    with mock.patch('redis.Redis', fakeredis.FakeRedis):
        with mock.patch('photonix.photos.utils.redis.redis_connection', fakeredis.FakeRedis()):
            yield


def test_downloading(tmpdir):
    from photonix.classifiers.style.model import StyleModel

    model_dir = tmpdir
    start = time.mktime(datetime.now().timetuple())
    model = StyleModel(lock_name=None, model_dir=model_dir)

    graph_path = str(Path(model_dir) / 'style' / 'graph.pb')
    assert os.stat(graph_path).st_size > 1024 * 10 * 10
    assert os.stat(graph_path).st_mtime > start
    with open(str(Path(model_dir) / 'style' / 'version.txt')) as f:
        content = f.read()
        assert content.strip() == str(model.version)


def test_color_predict():
    from photonix.classifiers.color.model import ColorModel

    model = ColorModel()
    snow = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    result = model.predict(snow)
    expected = [('Red', '0.163'), ('Gray', '0.163'), ('Azure', '0.126'), ('Amber', '0.112'), ('Green', '0.104'), ('Magenta', '0.102'), ('Turquoise',
                                                                                                                                        '0.058'), ('Teal', '0.049'), ('Lime', '0.038'), ('Purple', '0.029'), ('Orchid', '0.019'), ('Yellow', '0.018'), ('White', '0.017')]
    actual = [(x, '{:.3f}'.format(y)) for x, y in result]
    assert expected == actual


@mock.patch('photonix.classifiers.color.model.ColorModel.predict')
def test_color_predict_mock(mock_predict):
    from photonix.classifiers.color.model import ColorModel
    mock_predict.return_value = [['Red', 0.163], ['Gray', 0.163], ['Azure', 0.126], ['Amber', 0.112], ['Green', 0.104], ['Magenta', 0.102], [
        'Turquoise', 0.058], ['Teal', 0.049], ['Lime', 0.038], ['Purple', 0.029], ['Orchid', 0.019], ['Yellow', 0.018], ['White', 0.017]]
    model = ColorModel()
    snow = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    result = model.predict(snow)
    expected = [('Red', '0.163'), ('Gray', '0.163'), ('Azure', '0.126'), ('Amber', '0.112'), ('Green', '0.104'), ('Magenta', '0.102'), ('Turquoise',
                                                                                                                                        '0.058'), ('Teal', '0.049'), ('Lime', '0.038'), ('Purple', '0.029'), ('Orchid', '0.019'), ('Yellow', '0.018'), ('White', '0.017')]
    actual = [(x, '{:.3f}'.format(y)) for x, y in result]
    assert expected == actual


def test_location_predict():
    from photonix.classifiers.location.model import LocationModel

    model = LocationModel()

    # London, UK - Tests multiple polygons of the UK
    result = model.predict(location=[51.5304213, -0.1286445])
    assert result['country']['name'] == 'United Kingdom'
    assert result['city']['name'] == 'London'
    assert result['city']['distance'] == 1405
    assert result['city']['population'] == 7556900

    # In the sea near Oia, Santorini, Greece - Country is inferred from city
    result = model.predict(location=[36.4396445, 25.3560936])
    assert result['country']['name'] == 'Greece'
    assert result['city']['name'] == 'Oía'
    assert result['city']['distance'] == 3132
    assert result['city']['population'] == 3376

    # Too far off the coast of John o' Groats, Scotland, UK - No match
    result = model.predict(location=[58.6876742, -3.4206862])
    assert result['country'] == None
    assert result['city'] == None

    # Vernier, Switzerland - Tests country code mainly (CH can be China in some codings)
    result = model.predict(location=[46.1760906, 5.9929043])
    assert result['country']['name'] == 'Switzerland'
    assert result['country']['code'] == 'CH'
    assert result['city']['country_name'] == 'Switzerland'
    assert result['city']['country_code'] == 'CH'

    # In France but close to a 'city' in Belgium - City should be limited to within border of country
    result = model.predict(location=[51.074323, 2.547278])
    assert result['country']['name'] == 'France'
    assert result['city']['country_name'] == 'France'
    assert result['city']['name'] == 'Téteghem'


@mock.patch('photonix.classifiers.object.model.ObjectModel.predict')
def test_object_predict(mock_predict):
    from photonix.classifiers.object.model import ObjectModel
    mock_predict.return_value = [{'label': 'Tree', 'score': 0.602, 'significance': 0.134, 'x': 0.787, 'y': 0.374, 'width': 0.340, 'height': 0.655}, {
        'label': 'Tree', 'score': 0.525, 'significance': 0.016}, {'label': 'Tree', 'score': 0.453, 'significance': 0.025}]

    model = ObjectModel()
    snow = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    result = model.predict(snow)

    assert len(result) == 3

    assert result[0]['label'] == 'Tree'
    assert '{0:.3f}'.format(result[0]['score']) == '0.602'
    assert '{0:.3f}'.format(result[0]['significance']) == '0.134'
    assert '{0:.3f}'.format(result[0]['x']) == '0.787'
    assert '{0:.3f}'.format(result[0]['y']) == '0.374'
    assert '{0:.3f}'.format(result[0]['width']) == '0.340'
    assert '{0:.3f}'.format(result[0]['height']) == '0.655'

    assert result[1]['label'] == 'Tree'
    assert '{0:.3f}'.format(result[1]['score']) == '0.525'
    assert '{0:.3f}'.format(result[1]['significance']) == '0.016'

    assert result[2]['label'] == 'Tree'
    assert '{0:.3f}'.format(result[2]['score']) == '0.453'
    assert '{0:.3f}'.format(result[2]['significance']) == '0.025'


@mock.patch('photonix.classifiers.style.model.StyleModel.predict')
def test_style_predict(mock_predict):
    from photonix.classifiers.style.model import StyleModel
    mock_predict.side_effect = [[('serene', 0.990)], None]

    model = StyleModel()
    snow = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    result = model.predict(snow)

    assert len(result) == 1
    assert result[0][0] == 'serene'
    assert '{0:.3f}'.format(result[0][1]) == '0.990'

    # Check that there is no error when running with non-RGB image
    cmyk = str(Path(__file__).parent / 'photos' / 'cmyk.tif')
    result = model.predict(cmyk)
    assert result == None


@mock.patch('photonix.classifiers.face.model.FaceModel.retrain_face_similarity_index')
@mock.patch('photonix.classifiers.face.model.FaceModel.find_closest_face_tag_by_ann')
@mock.patch('photonix.classifiers.face.model.FaceModel.find_closest_face_tag_by_brute_force')
@mock.patch('photonix.classifiers.face.model.FaceModel.get_face_embedding')
@mock.patch('photonix.classifiers.face.model.FaceModel.__init__')
@mock.patch('photonix.classifiers.face.deepface.commons.distance.findEuclideanDistance')
@mock.patch('photonix.classifiers.face.deepface.commons.functions.find_input_shape')
def test_face_predict(mock_find_input_shape, mock_find_euclidean_distance, mock_init, mock_get_face_embedding, mock_brute_force, mock_ann, mock_retrain):
    mock_find_input_shape.return_value = (224, 224)
    from photonix.classifiers.face.deepface.commons.distance import \
        findEuclideanDistance
    from photonix.classifiers.face.model import FaceModel

    # Set up mock return values
    mock_init.return_value = None
    mock_get_face_embedding.return_value = [0.1, 0.2, 0.3]
    brute_force_results = [
        (1, 9.897),
        (2, 10.351),
        (2, 15.732)
    ]
    ann_results = [
        (1, 9.897),
        (2, 10.351),
        (2, 15.732)
    ]
    mock_brute_force.side_effect = brute_force_results
    mock_ann.side_effect = ann_results
    mock_retrain.return_value = None
    mock_find_euclidean_distance.side_effect = [9.897, 10.351, 15.732]

    TRAIN_FACES = [
        'Boris_Becker_0003.jpg',
        'Boris_Becker_0004.jpg',
        'David_Beckham_0001.jpg',
        'David_Beckham_0002.jpg',
    ]
    TEST_FACES = [
        # Test image, nearest match in TRAIN_FACES, distance (3DP)
        ('Boris_Becker_0005.jpg', 1, '9.897'),
        ('David_Beckham_0010.jpg', 2, '10.351'),
        ('Barbara_Becker_0001.jpg', 2, '15.732'),
    ]

    embedding_cache = []
    model = FaceModel()
    model.library_id = '00000000-0000-0000-0000-000000000000'

    # Calculate embeddings for training faces
    for fn in TRAIN_FACES:
        path = str(Path(__file__).parent / 'photos' / 'faces' / fn)
        image_data = Image.open(path)
        embedding = model.get_face_embedding(image_data)
        embedding_cache.append(embedding)

    training_data = [(i, embedding)
                     for i, embedding in enumerate(embedding_cache)]

    # Compare test faces using brute force Euclidian calculations
    for fn, expected_nearest, expected_distance in TEST_FACES:
        path = str(Path(__file__).parent / 'photos' / 'faces' / fn)
        image_data = Image.open(path)
        embedding = model.get_face_embedding(image_data)
        nearest, distance = model.find_closest_face_tag_by_brute_force(
            embedding, target_data=training_data)

        assert nearest == expected_nearest
        assert '{:.3f}'.format(distance) == expected_distance

    # Train ANN index
    model.retrain_face_similarity_index(training_data=training_data)

    # Compare test faces using ANN trained index
    for fn, expected_nearest, expected_distance in TEST_FACES:
        path = str(Path(__file__).parent / 'photos' / 'faces' / fn)
        image_data = Image.open(path)
        embedding = model.get_face_embedding(image_data)
        nearest, distance = model.find_closest_face_tag_by_ann(embedding)

        assert nearest == expected_nearest
        assert '{:.3f}'.format(distance) == expected_distance
        # assert abs(findEuclideanDistance(embedding, embedding_cache[nearest]) - distance) < 0.000001

    # Tidy up ANN model training
    for fn in [
        f'faces_{model.library_id}.ann',
        f'faces_tag_ids_{model.library_id}.json',
        f'retrained_version_{model.library_id}.txt',
    ]:
        try:
            os.remove(Path(settings.MODEL_DIR) / 'face' / fn)
        except:
            pass
