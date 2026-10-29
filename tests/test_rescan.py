from unittest import mock
import pytest
from .factories import LibraryFactory, LibraryPathFactory
from photonix.photos.models import LibraryPath

@pytest.mark.django_db
def test_library_path_rescan_success():
    library_path = LibraryPathFactory(type='St', backend_type='Lo')
    with mock.patch('photonix.photos.utils.organise.import_photos_in_place') as mock_import:
        library_path.rescan()
        mock_import.assert_called_once_with(library_path)

@pytest.mark.django_db
def test_library_path_rescan_wrong_type():
    library_path = LibraryPathFactory(type='Im', backend_type='Lo')
    with mock.patch('photonix.photos.utils.organise.import_photos_in_place') as mock_import:
        library_path.rescan()
        mock_import.assert_not_called()

@pytest.mark.django_db
def test_library_path_rescan_wrong_backend():
    library_path = LibraryPathFactory(type='St', backend_type='S3')
    with mock.patch('photonix.photos.utils.organise.import_photos_in_place') as mock_import:
        library_path.rescan()
        mock_import.assert_not_called()

@pytest.mark.django_db
def test_library_rescan():
    library = LibraryFactory()
    path1 = LibraryPathFactory(library=library, type='St', backend_type='Lo')
    path2 = LibraryPathFactory(library=library, type='Im', backend_type='Lo')

    with mock.patch.object(LibraryPath, 'rescan') as mock_rescan:
        library.rescan()
        assert mock_rescan.call_count == 2
        mock_rescan.assert_any_call()
