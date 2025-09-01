import datetime
from pathlib import Path
import pytest

from .factories import LibraryUserFactory
from .utils import get_graphql_content
from photonix.photos.models import Tag, PhotoTag, Library, LibraryPath, Photo
from photonix.photos.utils.db import record_photo
from photonix.accounts.models import User


@pytest.fixture
def setup_data(db, api_client):
    """Create default user, library, photos and login."""
    library_user = LibraryUserFactory()
    library = library_user.library
    user = library_user.user
    user.set_password('demo123456')
    user.save()

    # Authenticate the user for the client
    api_client.set_user(user)

    LibraryPath.objects.create(library=library, type="St", backend_type='Lo', path='/data/photos/')
    snow_path = str(Path(__file__).parent / 'photos' / 'snow.jpg')
    snow_photo = record_photo(snow_path, library)

    tree_path = str(Path(__file__).parent / 'photos' / 'tree.jpg')
    tree_photo = record_photo(tree_path, library)

    return {
        'library_user': library_user,
        'library': library,
        'user': user,
        'snow_photo': snow_photo,
        'tree_photo': tree_photo,
        'password': 'demo123456',
    }


@pytest.mark.django_db
class TestGraphQL:
    """Test cases for graphql API's."""

    def test_fix347(self, setup_data):
        # Test fix 347 - Photos with same date are not imported
        library = setup_data['library']
        path_photo1 = str(Path(__file__).parent / 'photos' / 'photo_no_metadata_1.jpg')
        Path(path_photo1).touch()

        path_photo2 = str(Path(__file__).parent / 'photos' / 'photo_no_metadata_2.jpg')
        Path(path_photo2).touch()

        photo1 = record_photo(path_photo1, library)
        photo2 = record_photo(path_photo2, library)

        assert photo1 != photo2

    def test_user_login_environment(self, api_client, setup_data):
        """Test user logged in successfully or not."""
        environment_query = """
            query{
                environment {
                  demo
                  firstRun
                  form
                  userId
                  libraryId
                  libraryPathId
                }
            }
        """
        response = api_client.post_graphql(environment_query)
        assert response.status_code == 200
        data = get_graphql_content(response)
        assert not data['data']['environment']['firstRun']
        assert data['data']['environment']['userId'] == str(setup_data['user'].id)

    def test_get_photo(self, api_client, setup_data):
        query = """
            query PhotoQuery($id: UUID) {
                photo(id: $id) {
                    url
                }
            }
        """
        response = api_client.post_graphql(query, {'id': str(setup_data['snow_photo'].id)})
        assert response.status_code == 200
        data = get_graphql_content(response)
        assert data['data']['photo']['url'].startswith('/thumbnails')

    def test_get_photos(self, api_client, setup_data):
        query = """
            {
                allPhotos {
                    edges {
                        node {
                            url
                        }
                    }
                }
            }
        """
        response = api_client.post_graphql(query, {'id': str(setup_data['snow_photo'].id)})
        assert response.status_code == 200
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 2
        assert data['data']['allPhotos']['edges'][0]['node']['url'].startswith('/thumbnails')

    def test_filter_photos(self, api_client, setup_data):
        tree_tag, _ = Tag.objects.get_or_create(library=setup_data['library'], name='Tree', type='O')
        PhotoTag.objects.get_or_create(photo=setup_data['snow_photo'], tag=tree_tag, confidence=1.0)
        multi_filter = 'library_id:{0} tag:{1}'.format(setup_data['library'].id, tree_tag.id)
        query = """
            query PhotoQuery($filters: String) {
                allPhotos(multiFilter: $filters) {
                    edges {
                        node {
                            id
                        }
                    }
                }
            }
        """
        response = api_client.post_graphql(query, {'filters': multi_filter})

        assert response.status_code == 200
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1
        assert data['data']['allPhotos']['edges'][0]['node']['id'] == str(setup_data['snow_photo'].id)

        # Add 'Tree' tag to another photo. Querying again should return 2 photos
        PhotoTag.objects.get_or_create(photo=setup_data['tree_photo'], tag=tree_tag, confidence=1.0)
        response = api_client.post_graphql(query, {'filters': multi_filter})

        assert response.status_code == 200
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 2

        # Add 'Tree' to the last photo again (allowed). Querying should not return duplicates
        PhotoTag.objects.get_or_create(photo=setup_data['tree_photo'], tag=tree_tag, confidence=0.9)
        response = api_client.post_graphql(query, {'filters': multi_filter})
        assert response.status_code == 200
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 2

    def test_all_libraries(self, api_client, setup_data):
        """Test list of libraries."""
        query = """
            {
                allLibraries {
                    id
                    name
                }
            }
        """
        response = api_client.post_graphql(query)
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert len(data['data']['allLibraries']) == 1
        assert data['data']['allLibraries'][0]['id'] == str(setup_data['library'].id)
        assert data['data']['allLibraries'][0]['name'] == setup_data['library'].name

    def test_user_profile_data(self, api_client, setup_data):
        """Test profile data."""
        query = """
            {
                profile {
                  id
                  username
                  email
                }
            }
        """
        response = api_client.post_graphql(query)
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['profile']['id'] == str(setup_data['user'].id)
        assert data['data']['profile']['username'] == setup_data['user'].username
        assert data['data']['profile']['email'] == setup_data['user'].email

    def test_library_setting_data(self, api_client, setup_data):
        """Test library setting data."""
        query = """
            query LibrarySetting($libraryId: UUID) {
                librarySetting(libraryId: $libraryId) {
                  library {
                    name
                    classificationColorEnabled
                    classificationStyleEnabled
                    classificationObjectEnabled
                    classificationLocationEnabled
                    classificationFaceEnabled
                  }
                  sourceFolder
                }
            }
        """
        response = api_client.post_graphql(query, {'libraryId': str(setup_data['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['librarySetting']['library']['name'] == setup_data['library'].name
        assert data['data']['librarySetting']['library']['classificationColorEnabled']
        assert data['data']['librarySetting']['library']['classificationStyleEnabled']
        assert data['data']['librarySetting']['library']['classificationObjectEnabled']
        assert data['data']['librarySetting']['library']['classificationLocationEnabled']
        assert data['data']['librarySetting']['library']['classificationFaceEnabled']
        assert data['data']['librarySetting']['sourceFolder'] == setup_data['library'].paths.all()[0].path

    def test_library_update_style_enabled_mutation(self, api_client, setup_data):
        """Test library updateStyleEnabled mutation response."""
        mutation = """
            mutation updateStyleEnabled(
                $classificationStyleEnabled: Boolean!
                $libraryId: ID
              ) {
                updateStyleEnabled(
                  input: {
                    classificationStyleEnabled: $classificationStyleEnabled
                    libraryId: $libraryId
                  }
                ) {
                  classificationStyleEnabled
                }
              }
        """
        response = api_client.post_graphql(mutation, {'classificationStyleEnabled': True, 'libraryId': str(setup_data['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['updateStyleEnabled']['classificationStyleEnabled']

    def test_library_update_color_enabled_mutation(self, api_client, setup_data):
        """Test library updateColorEnabled mutation response."""
        mutation = """
            mutation updateColorEnabled(
                $classificationColorEnabled: Boolean!
                $libraryId: ID
              ) {
                updateColorEnabled(
                  input: {
                    classificationColorEnabled: $classificationColorEnabled
                    libraryId: $libraryId
                  }
                ) {
                  classificationColorEnabled
                }
            }
        """
        response = api_client.post_graphql(mutation, {'classificationColorEnabled': True, 'libraryId': str(setup_data['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['updateColorEnabled']['classificationColorEnabled']

    def test_library_update_location_enabled_mutation(self, api_client, setup_data):
        """Test library updateLocationEnabled mutation response."""
        mutation = """
            mutation updateLocationEnabled(
                $classificationLocationEnabled: Boolean!
                $libraryId: ID
              ) {
                updateLocationEnabled(
                  input: {
                    classificationLocationEnabled: $classificationLocationEnabled
                    libraryId: $libraryId
                  }
                ) {
                  classificationLocationEnabled
                }
            }
        """
        response = api_client.post_graphql(mutation, {'classificationLocationEnabled': False, 'libraryId': str(setup_data['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert not data['data']['updateLocationEnabled']['classificationLocationEnabled']

    def test_library_update_object_enabled_mutation(self, api_client, setup_data):
        """Test library updateObjectEnabled mutation response."""
        mutation = """
            mutation updateObjectEnabled(
                $classificationObjectEnabled: Boolean!
                $libraryId: ID
              ) {
                updateObjectEnabled(
                  input: {
                    classificationObjectEnabled: $classificationObjectEnabled
                    libraryId: $libraryId
                  }
                ) {
                  classificationObjectEnabled
                }
            }
        """
        response = api_client.post_graphql(mutation, {'classificationObjectEnabled': False, 'libraryId': str(setup_data['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert not data['data']['updateObjectEnabled']['classificationObjectEnabled']

    def test_library_update_source_folder_mutation(self, api_client, setup_data):
        """Test library updateSourceFolder mutation response."""
        mutation = """
            mutation updateSourceFolder($sourceFolder: String!, $libraryId: ID) {
                updateSourceFolder(
                  input: { sourceFolder: $sourceFolder, libraryId: $libraryId }
                ) {
                  sourceFolder
                }
            }
        """
        response = api_client.post_graphql(mutation, {'sourceFolder': '/data/photos/', 'libraryId': str(setup_data['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['updateSourceFolder']['sourceFolder'] == setup_data['library'].paths.all()[0].path

    def test_change_password_mutation(self, api_client, setup_data):
        """Test change password mutation response."""
        mutation = """
            mutation changePassword (
                $oldPassword: String!,
                $newPassword: String!
              ) {
                  changePassword(oldPassword:$oldPassword,newPassword:$newPassword) {
                    ok
                }
              }
        """
        response = api_client.post_graphql(mutation, {'oldPassword': setup_data['password'], 'newPassword': 'download123'})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['changePassword']['ok']

    def test_after_signup_api(self, api_client, setup_data):
        """Test after signup api response."""
        query = """
            {
              afterSignup {
                token
                refreshToken
              }
            }
        """
        response = api_client.post_graphql(query)
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['afterSignup']['token']
        assert data['data']['afterSignup']['refreshToken']

    def test_photo_rating_mutation(self, api_client, setup_data):
        """Test photo rating mutation response."""
        mutation = """
            mutation photoRating(
               $photoId: ID!,$starRating:Int!,
               ) {
                photoRating(photoId: $photoId,starRating:$starRating) {
                    photo {
                      starRating
                      aperture
                      takenBy
                      flash
                    }
                }
            }
        """
        response = api_client.post_graphql(mutation, {'photoId': str(setup_data['snow_photo'].id), 'starRating': 4})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['photoRating']['photo']['starRating'] == 4
        assert data['data']['photoRating']['photo']['aperture'] == setup_data['snow_photo'].aperture

    def test_create_generic_tag_mutation(self, api_client, setup_data):
        """Test create_generic_tag mutation response."""
        mutation = """
            mutation createGenericTag(
                $name: String!,
                $photoId: ID!
              ) {
                createGenericTag(name: $name, photoId: $photoId) {
                  ok
                  photoTagId
                  tagId
                  name
                }
            }
        """
        response = api_client.post_graphql(
            mutation, {'name': 'snow-photo', 'photoId': str(setup_data['snow_photo'].id)})
        data = get_graphql_content(response)
        created_generic_tag_obj = Tag.objects.get(name='snow-photo')
        assert data['data']['createGenericTag']['ok']
        assert data['data']['createGenericTag']['photoTagId'] == str(created_generic_tag_obj.photo_tags.all()[0].id)
        assert data['data']['createGenericTag']['tagId'] == str(created_generic_tag_obj.id)
        assert data['data']['createGenericTag']['name'] == 'snow-photo'

    def test_remove_generic_tag_mutation(self, api_client, setup_data):
        """Test remove_generic_tag mutation response."""
        mutation = """
            mutation createGenericTag(
                $name: String!,
                $photoId: ID!
              ) {
                createGenericTag(name: $name, photoId: $photoId) {
                  ok
                  photoTagId
                  tagId
                  name
                }
            }
        """
        response = api_client.post_graphql(
            mutation, {'name': 'snow-photo', 'photoId': str(setup_data['snow_photo'].id)})
        data = get_graphql_content(response)
        created_generic_tag_obj = Tag.objects.get(name='snow-photo')
        assert data['data']['createGenericTag']['ok']
        assert data['data']['createGenericTag']['photoTagId'] == str(created_generic_tag_obj.photo_tags.all()[0].id)
        assert data['data']['createGenericTag']['tagId'] == str(created_generic_tag_obj.id)
        assert data['data']['createGenericTag']['name'] == 'snow-photo'

        mutation = """
            mutation removeGenericTag(
                $tagId: ID!,
                $photoId: ID!
              ) {
                removeGenericTag(tagId:$tagId, photoId:$photoId) {
                  ok
                }
              }
        """
        response = api_client.post_graphql(
            mutation, {'tagId': str(created_generic_tag_obj.id), 'photoId': str(setup_data['snow_photo'].id)})
        data = get_graphql_content(response)
        assert data['data']['removeGenericTag']['ok']
        assert not Photo.objects.get(id=setup_data['snow_photo'].id).photo_tags.filter(id=created_generic_tag_obj.id).exists()
        assert not Tag.objects.filter(id=created_generic_tag_obj.id).exists()

    def test_get_photo_detail_api(self, api_client, setup_data):
        """Test valid resposne of get photo api."""
        query = """
            query Photo($id: UUID) {
                photo(id: $id) {
                  id
                  takenAt
                  takenBy
                  aperture
                  exposure
                  isoSpeed
                  focalLength
                  flash
                  meteringMode
                  driveMode
                  shootingMode
                  starRating
                  camera {
                    id
                    make
                    model
                  }
                  lens {
                    id
                    name
                  }
                  location
                  altitude
                  url
                  locationTags {
                    id
                    tag {
                      id
                      name
                      parent {
                        id
                      }
                    }
                  }
                  objectTags {
                    id
                    tag {
                      name
                    }
                    positionX
                    positionY
                    sizeX
                    sizeY
                  }
                  colorTags {
                    id
                    tag {
                      name
                    }
                    significance
                  }
                  styleTags {
                    id
                    tag {
                      name
                    }
                  }
                  genericTags {
                    id
                    tag {
                      id
                      name
                    }
                  }
                  width
                  height
                }
              }
        """
        tree_tag, _ = Tag.objects.get_or_create(library=setup_data['library'], name='Tree', type='O')
        tree_photo_tag, _ = PhotoTag.objects.get_or_create(photo=setup_data['tree_photo'], tag=tree_tag, confidence=1.0)
        response = api_client.post_graphql(query, {'id': str(setup_data['tree_photo'].id)})
        assert response.status_code == 200
        data = get_graphql_content(response)
        photo_data = data['data']['photo']
        tree_photo = setup_data['tree_photo']
        assert photo_data['id'] == str(tree_photo.id)
        assert photo_data['aperture'] == tree_photo.aperture
        assert photo_data['exposure'] == tree_photo.exposure
        assert photo_data['isoSpeed'] == tree_photo.iso_speed
        assert str(photo_data['focalLength']) == tree_photo.focal_length
        assert photo_data['meteringMode'] == tree_photo.metering_mode
        assert not photo_data['flash']
        assert photo_data['camera']['id'] == str(tree_photo.camera.id)
        assert photo_data['width'] == tree_photo.dimensions[0]
        assert photo_data['height'] == tree_photo.dimensions[1]
        assert photo_data['objectTags'][0]['id'] == str(tree_photo_tag.id)
        assert photo_data['objectTags'][0]['tag']['name'] == tree_tag.name
        assert photo_data['url'].startswith('/thumbnails')

    def test_filter_photos_by_date_api(self, api_client, setup_data):
        """Test photo filtering API by passing date with all scenarios."""
        tree_tag, _ = Tag.objects.get_or_create(library=setup_data['library'], name='Tree', type='O')
        PhotoTag.objects.get_or_create(photo=setup_data['tree_photo'], tag=tree_tag, confidence=1.0)
        taken_at_date = setup_data['snow_photo'].taken_at
        query = """
            query Photos($filters: String) {
                allPhotos(multiFilter: $filters) {
                  edges {
                    node {
                      id
                      location
                      starRating
                    }
                  }
                }
            }
        """

        # Filter photos by current year only example 'library_id:{0} 2021'
        multi_filter = 'library_id:{0} {1}'.format(setup_data['library'].id, taken_at_date.year)
        response = api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 2
        assert data['data']['allPhotos']['edges'][1]['node']['id'] == str(setup_data['snow_photo'].id)
        assert data['data']['allPhotos']['edges'][0]['node']['id'] == str(setup_data['tree_photo'].id)

        # Filter photos by month name only example 'library_id:{0} March 2017'
        multi_filter = 'library_id:{0} {1} {2}'.format(setup_data['library'].id, taken_at_date.strftime('%B').lower(), taken_at_date.year)
        response = api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

        # Filter photos by first 3 letter of month name only example 'library_id:{0} Mar' 2017
        multi_filter = 'library_id:{0} {1} {2}'.format(setup_data['library'].id, taken_at_date.strftime('%b').lower(), taken_at_date.year)
        response = api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

        # Filter photos by date and current month name. example 'library_id:{0} March 18 2017'
        multi_filter = 'library_id:{0} {1} {2} {3}'.format(setup_data['library'].id, taken_at_date.strftime('%b').lower(), taken_at_date.strftime("%d"), taken_at_date.year)
        response = api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

        # Filter photos by date and current month name and year example 'library_id:{0} 18 March 2021'.
        multi_filter = 'library_id:{0} {1} {2} {3}'.format(setup_data['library'].id, taken_at_date.strftime("%d"), taken_at_date.strftime('%b').lower(), taken_at_date.year)
        response = api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

        # Filter photos by date having some other words like in of etc example 'library_id:{0} party in mar 2021'.
        multi_filter = 'library_id:{0} party in {1} {2}'.format(setup_data['library'].id, taken_at_date.strftime('%b').lower(), taken_at_date.year)
        response = api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 0  # Because photos having this date but any photo not having party tag.

        # Filter photos by date having some other words like in of etc and any tag name with date example 'library_id:{0} Tree in mar 2021'.
        taken_at_date = setup_data['tree_photo'].taken_at
        multi_filter = 'library_id:{0} Tree in {1} {2}'.format(setup_data['library'].id, taken_at_date.strftime('%b').lower(), taken_at_date.year)
        response = api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

        # Filter photos by tag id and month name example 'library_id:{0} tag:id mar 2018'.
        multi_filter = 'library_id:{0} tag:{1} {2} {3}'.format(setup_data['library'].id, tree_tag.id, taken_at_date.strftime('%B').lower(), taken_at_date.year)
        response = api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

    def test_filter_photos_for_map_api(self, api_client, setup_data):
        """Test photo filtering API for map."""
        tree_tag, _ = Tag.objects.get_or_create(library=setup_data['library'], name='Tree', type='O')
        PhotoTag.objects.get_or_create(photo=setup_data['tree_photo'], tag=tree_tag, confidence=1.0)
        taken_at_date = setup_data['tree_photo'].taken_at
        multi_filter = 'library_id:{0} tag:{1} {2} {3}'.format(setup_data['library'].id, tree_tag.id, taken_at_date.strftime('%B').lower(), taken_at_date.year)
        query = """
            query Photos($filters: String) {
                mapPhotos(multiFilter: $filters) {
                  edges {
                    node {
                      id
                      url
                      location
                    }
                  }
                }
              }
        """
        response = api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['mapPhotos']['edges']) == 1
        assert data['data']['mapPhotos']['edges'][0]['node']['id'] == str(setup_data['tree_photo'].id)
        assert data['data']['mapPhotos']['edges'][0]['node']['url'].startswith('/thumbnails')
        assert data['data']['mapPhotos']['edges'][0]['node']['location']

    def test_filter_with_exposure_range_api(self, api_client, setup_data):
        """Test photo filtering by exposure_range example 1/1124."""
        multi_filter = 'library_id:{0} exposure:1/4000-1/1600-1/1124-1/1000-1/800-1/500-1/400'.format(setup_data['library'].id)
        query = """
            query Photos($filters: String) {
                mapPhotos(multiFilter: $filters) {
                  edges {
                    node {
                      id
                      url
                      location
                    }
                  }
                }
              }
        """
        response = api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        # mapPhotos query exclude(latitude__isnull=True, longitude__isnull=True) thats why result return only one photo.
        assert len(data['data']['mapPhotos']['edges']) == 1

    def test_response_of_get_filters_api(self, api_client, setup_data):
        """Test response of get filters api."""
        object_type_tag, _ = Tag.objects.get_or_create(library=setup_data['library'], name='Tree', type='O')
        PhotoTag.objects.get_or_create(photo=setup_data['tree_photo'], tag=object_type_tag, confidence=1.0)
        color_type_tag, _ = Tag.objects.get_or_create(library=setup_data['library'], name='Yellow', type='C')
        PhotoTag.objects.get_or_create(photo=setup_data['tree_photo'], tag=color_type_tag, confidence=1.0)
        white_color_tag, _ = Tag.objects.get_or_create(library=setup_data['library'], name='White', type='C')
        PhotoTag.objects.get_or_create(photo=setup_data['snow_photo'], tag=white_color_tag, confidence=1.0)
        multi_filter = 'aperture:1.3-10'
        query = """
            query AllFilters($libraryId: UUID, $multiFilter: String) {
                allLocationTags(libraryId: $libraryId, multiFilter: $multiFilter) {
                  id
                  name
                  parent {
                    id
                  }
                }
                allObjectTags(libraryId: $libraryId, multiFilter: $multiFilter) {
                  id
                  name
                }
                allPersonTags(libraryId: $libraryId, multiFilter: $multiFilter) {
                  id
                  name
                }
                allColorTags(libraryId: $libraryId, multiFilter: $multiFilter) {
                  id
                  name
                }
                allStyleTags(libraryId: $libraryId, multiFilter: $multiFilter) {
                  id
                  name
                }
                allEventTags(libraryId: $libraryId, multiFilter: $multiFilter) {
                  id
                  name
                }
                allCameras(libraryId: $libraryId) {
                  id
                  make
                  model
                }
                allLenses(libraryId: $libraryId) {
                  id
                  name
                }
                allGenericTags(libraryId: $libraryId, multiFilter: $multiFilter) {
                  name
                  id
                }
                allApertures(libraryId: $libraryId)
                allExposures(libraryId: $libraryId)
                allIsoSpeeds(libraryId: $libraryId)
                allFocalLengths(libraryId: $libraryId)
                allMeteringModes(libraryId: $libraryId)
                allDriveModes(libraryId: $libraryId)
                allShootingModes(libraryId: $libraryId)
              }
        """
        response = api_client.post_graphql(query, {'libraryId': str(setup_data['library'].id), 'multiFilter': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allObjectTags']) == 1
        assert data['data']['allObjectTags'][0]['name'] == object_type_tag.name
        assert len(data['data']['allColorTags']) == 2
        assert data['data']['allColorTags'][0]['name'] == white_color_tag.name
        assert data['data']['allColorTags'][1]['name'] == color_type_tag.name
        assert data['data']['allApertures'][0] == setup_data['tree_photo'].aperture
        assert data['data']['allCameras'][0]['id'] == str(setup_data['snow_photo'].camera.id)
        assert str(data['data']['allFocalLengths'][0]) == setup_data['snow_photo'].focal_length


@pytest.mark.django_db
class TestGraphQLOnboarding:
    """Check onboarding(user sign up) process queries."""

    def test_onboarding_steps(self, api_client):
        """Check all the steps of onboarding(user sign up) process."""
        environment_query = """
            query{
                environment {
                  demo
                  firstRun
                  form
                  userId
                  libraryId
                  libraryPathId
                }
            }
        """
        response = api_client.post_graphql(environment_query)
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['environment']['firstRun']
        assert data['data']['environment']['form'] == 'has_set_personal_info'
        assert not User.objects.all().count()
        mutation = """
            mutation ($username: String!,$password:String!,$password1:String!) {
                createUser(username: $username,password:$password,password1:$password1) {
                    hasSetPersonalInfo
                    userId
                }
            }
        """
        response = api_client.post_graphql(
            mutation, {'username': 'demo', 'password': 'demo12345', 'password1': 'demo12345'})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['createUser']['hasSetPersonalInfo']
        assert User.objects.all().count() == 1
        assert User.objects.first().has_set_personal_info
        assert not User.objects.first().has_created_library
        assert not response.wsgi_request.user.username
        mutation = """
            mutation ($name: String!,$backendType: String!,$path: String!,$userId: ID!)
                {
                    createLibrary(input:{
                        name:$name,
                        backendType:$backendType,
                        path:$path,
                        userId:$userId
                    }) {
                        hasCreatedLibrary
                        userId
                        libraryId
                        libraryPathId
                    }
                }
        """
        response = api_client.post_graphql(
            mutation, {
                'name': 'demo library', 'backendType': 'Lo',
                'path': '/data/photos', 'userId': data['data']['createUser']['userId'],
            })
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['createLibrary']['hasCreatedLibrary']
        assert User.objects.first().has_created_library
        assert not User.objects.first().has_configured_importing
        mutation = """
            mutation ($watchForChanges: Boolean!,$addAnotherPath: Boolean!,$importPath: String!,
                $deleteAfterImport: Boolean!,$userId: ID!,$libraryId: ID!,$libraryPathId: ID!)
                {
                    PhotoImporting(input:{
                        watchForChanges:$watchForChanges,
                        addAnotherPath:$addAnotherPath,
                        importPath:$importPath,
                        deleteAfterImport:$deleteAfterImport,
                        userId:$userId,
                        libraryId:$libraryId,
                        libraryPathId:$libraryPathId
                    }) {
                        hasConfiguredImporting
                        userId
                        libraryId
                    }
                }
        """
        response = api_client.post_graphql(
            mutation, {
                'watchForChanges': True, 'addAnotherPath': True,
                'importPath': '/data/photos', 'deleteAfterImport': True,
                'userId': data['data']['createLibrary']['userId'],
                'libraryId': data['data']['createLibrary']['libraryId'],
                'libraryPathId': data['data']['createLibrary']['libraryPathId']
            })
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['PhotoImporting']['hasConfiguredImporting']
        assert User.objects.first().has_configured_importing
        assert not User.objects.first().has_configured_image_analysis
        mutation = """
            mutation (
                $classificationColorEnabled: Boolean!,
                $classificationStyleEnabled: Boolean!,
                $classificationObjectEnabled: Boolean!,
                $classificationLocationEnabled: Boolean!,
                $classificationFaceEnabled: Boolean!,
                $userId: ID!,$libraryId: ID!,
                ) {
                    imageAnalysis(input:{
                        classificationColorEnabled:$classificationColorEnabled,
                        classificationStyleEnabled:$classificationStyleEnabled,
                        classificationObjectEnabled:$classificationObjectEnabled,
                        classificationLocationEnabled:$classificationLocationEnabled,
                        classificationFaceEnabled:$classificationFaceEnabled,
                        userId:$userId,
                        libraryId:$libraryId,
                    }) {
                        hasConfiguredImageAnalysis
                        userId
                    }
                }
        """
        library_id = data['data']['PhotoImporting']['libraryId']
        response = api_client.post_graphql(
            mutation, {
                'classificationColorEnabled': True,
                'classificationStyleEnabled': True,
                'classificationObjectEnabled': False,
                'classificationLocationEnabled': False,
                'classificationFaceEnabled': False,
                'userId': data['data']['PhotoImporting']['userId'],
                'libraryId': data['data']['PhotoImporting']['libraryId'],
            })
        data = get_graphql_content(response)
        library = Library.objects.get(pk=library_id)
        assert User.objects.all().count() == 1
        assert response.status_code == 200
        assert data['data']['imageAnalysis']['hasConfiguredImageAnalysis']
        assert library.classification_color_enabled
        assert library.classification_style_enabled
        assert not library.classification_object_enabled
        assert not library.classification_location_enabled
        assert User.objects.filter(
            username='demo', has_set_personal_info=True,
            has_created_library=True, has_configured_importing=True,
            has_configured_image_analysis=True).exists()
        assert response.wsgi_request.user.username == 'demo'
