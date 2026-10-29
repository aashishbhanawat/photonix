import sys
from unittest import mock

# Standard mock for missing environment dependencies to allow test collection on host
mock_modules = {
    'django': mock.MagicMock(),
    'django.conf': mock.MagicMock(),
    'celery': mock.MagicMock(),
    'photonix.photos.utils.organise': mock.MagicMock(),
    'photonix.photos.utils.thumbnails': mock.MagicMock(),
}

with mock.patch.dict('sys.modules', mock_modules):
    import photonix.photos.consumers as consumers

def test_rescan_photos():
    with mock.patch.object(consumers, 'import_photos_in_place') as mock_import, \
         mock.patch.object(consumers, 'settings') as mock_settings:
        mock_settings.PHOTO_OUTPUT_DIRS = [
            {'PATH': '/path/one'},
            {'PATH': '/path/two'}
        ]
        consumers.rescan_photos(None)
        assert mock_import.call_count == 2
        mock_import.assert_any_call('/path/one')
        mock_import.assert_any_call('/path/two')

def test_photo_added_success():
    with mock.patch.object(consumers, 'generate_thumbnails_for_photo') as mock_generate:
        message = {'text': '{"id": 123}'}
        consumers.photo_added(message)
        mock_generate.assert_called_once_with(123)

def test_photo_added_no_message():
    with mock.patch.object(consumers, 'generate_thumbnails_for_photo') as mock_generate:
        consumers.photo_added(None)
        mock_generate.assert_not_called()

def test_photo_added_no_id():
    with mock.patch.object(consumers, 'generate_thumbnails_for_photo') as mock_generate:
        message = {'text': '{"id": null}'}
        consumers.photo_added(message)
        mock_generate.assert_not_called()
