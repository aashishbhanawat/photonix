from unittest import mock
from photonix.classifiers.runners import results_for_model_on_photo

@mock.patch('photonix.classifiers.runners.get_photo_by_any_type')
def test_results_for_model_on_photo_with_photo_instance(mock_get_photo):
    # Setup
    mock_model = mock.Mock()
    mock_photo = mock.Mock()
    mock_photo.base_image_path = '/path/to/photo.jpg'
    mock_get_photo.return_value = mock_photo
    mock_model.predict.return_value = [{'label': 'test', 'score': 0.9}]

    photo_id = 'some-uuid'

    # Execute
    photo, results = results_for_model_on_photo(mock_model, photo_id)

    # Verify
    mock_get_photo.assert_called_once_with(photo_id, mock_model)
    mock_model.predict.assert_called_once_with('/path/to/photo.jpg')
    assert photo == mock_photo
    assert results == [{'label': 'test', 'score': 0.9}]

@mock.patch('photonix.classifiers.runners.get_photo_by_any_type')
def test_results_for_model_on_photo_with_raw_path(mock_get_photo):
    # Setup
    mock_model = mock.Mock()
    mock_get_photo.return_value = None
    mock_model.predict.return_value = [{'label': 'test', 'score': 0.8}]

    photo_id = '/path/to/raw/photo.jpg'

    # Execute
    photo, results = results_for_model_on_photo(mock_model, photo_id)

    # Verify
    mock_get_photo.assert_called_once_with(photo_id, mock_model)
    mock_model.predict.assert_called_once_with(photo_id)
    assert photo is None
    assert results == [{'label': 'test', 'score': 0.8}]
