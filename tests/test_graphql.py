import datetime
import os
from pathlib import Path
import pytest

from .factories import LibraryUserFactory
from .utils import get_graphql_content
from photonix.photos.models import Tag, PhotoTag, Library, LibraryPath, Photo
from photonix.photos.utils.db import record_photo
from photonix.accounts.models import User

@pytest.fixture
def db_setup(db):
    """Set up the database with a library, user, and photos."""
    library_user = LibraryUserFactory()
    library = library_user.library
    user = library_user.user
    user.set_password('demo123456')
    user.save()

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

@pytest.fixture
def logged_in_api_client(api_client, db_setup):
    """Return an API client that is logged in as the test user."""
    user = db_setup['user']
    password = db_setup['password']

    login_mutation = """
        mutation TokenAuth($username: String!, $password: String!) {
            tokenAuth(username: $username, password: $password) {
              token
              refreshToken
            }
          }
    """
    api_client.set_user(user)
    api_client.post_graphql(login_mutation, {'username': user.username, 'password': password})
    return api_client

@pytest.mark.django_db
class TestGraphQL:
    def test_fix347(self, logged_in_api_client, db_setup):
        path_photo1 = str(Path(__file__).parent / 'photos' / 'photo_no_metadata_1.jpg')
        Path(path_photo1).touch()

        path_photo2 = str(Path(__file__).parent / 'photos' / 'photo_no_metadata_2.jpg')
        Path(path_photo2).touch()

        photo1 = record_photo(path_photo1, db_setup['library'])
        photo2 = record_photo(path_photo2, db_setup['library'])

        assert(not photo1 == photo2)

    def test_user_login_environment(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(environment_query)
        assert response.status_code == 200
        data = get_graphql_content(response)
        assert not data['data']['environment']['firstRun']

    def test_get_photo(self, logged_in_api_client, db_setup):
        query = """
            query PhotoQuery($id: UUID) {
                photo(id: $id) {
                    url
                }
            }
        """
        response = logged_in_api_client.post_graphql(query, {'id': str(db_setup['snow_photo'].id)})
        assert response.status_code == 200
        data = get_graphql_content(response)
        assert data['data']['photo']['url'].startswith('/thumbnails')

    def test_get_photos(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(query, {'id': str(db_setup['snow_photo'].id)})
        assert response.status_code == 200
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 2
        assert data['data']['allPhotos']['edges'][0]['node']['url'].startswith('/thumbnails')

    def test_filter_photos(self, logged_in_api_client, db_setup):
        tree_tag, _ = Tag.objects.get_or_create(library=db_setup['library'], name='Tree', type='O')
        PhotoTag.objects.get_or_create(photo=db_setup['snow_photo'], tag=tree_tag, confidence=1.0)
        multi_filter = 'library_id:{0} tag:{1}'.format(db_setup['library'].id,tree_tag.id)
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
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})

        assert response.status_code == 200
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1
        assert data['data']['allPhotos']['edges'][0]['node']['id'] == str(db_setup['snow_photo'].id)

        PhotoTag.objects.get_or_create(photo=db_setup['tree_photo'], tag=tree_tag, confidence=1.0)
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})

        assert response.status_code == 200
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 2

        PhotoTag.objects.get_or_create(photo=db_setup['tree_photo'], tag=tree_tag, confidence=0.9)
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        assert response.status_code == 200
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 2

    def test_all_libraries(self, logged_in_api_client, db_setup):
        query = """
            {
                allLibraries {
                    id
                    name
                }
            }
        """
        response = logged_in_api_client.post_graphql(query)
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert len(data['data']['allLibraries']) == 1
        assert data['data']['allLibraries'][0]['id'] == str(db_setup['library'].id)
        assert data['data']['allLibraries'][0]['name'] == db_setup['library'].name

    def test_user_profile_data(self, logged_in_api_client, db_setup):
        query = """
            {
                profile {
                  id
                  username
                  email
                }
            }
        """
        response = logged_in_api_client.post_graphql(query)
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['profile']['id'] == str(db_setup['user'].id)
        assert data['data']['profile']['username'] == db_setup['user'].username
        assert data['data']['profile']['email'] == db_setup['user'].email

    def test_library_setting_data(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(query, {'libraryId': str(db_setup['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['librarySetting']['library']['name'] == db_setup['library'].name
        assert data['data']['librarySetting']['library']['classificationColorEnabled']
        assert data['data']['librarySetting']['library']['classificationStyleEnabled']
        assert data['data']['librarySetting']['library']['classificationObjectEnabled']
        assert data['data']['librarySetting']['library']['classificationLocationEnabled']
        assert data['data']['librarySetting']['library']['classificationFaceEnabled']
        assert data['data']['librarySetting']['sourceFolder'] == db_setup['library'].paths.all()[0].path

    def test_library_update_style_enabled_mutation(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(mutation, {'classificationStyleEnabled':True,'libraryId': str(db_setup['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['updateStyleEnabled']['classificationStyleEnabled']

    def test_library_update_color_enabled_mutation(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(mutation, {'classificationColorEnabled':True,'libraryId': str(db_setup['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['updateColorEnabled']['classificationColorEnabled']

    def test_library_update_location_enabled_mutation(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(mutation, {'classificationLocationEnabled':False,'libraryId': str(db_setup['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert not data['data']['updateLocationEnabled']['classificationLocationEnabled']

    def test_library_update_object_enabled_mutation(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(mutation, {'classificationObjectEnabled':False,'libraryId': str(db_setup['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert not data['data']['updateObjectEnabled']['classificationObjectEnabled']

    def test_library_update_source_folder_mutation(self, logged_in_api_client, db_setup):
        mutation = """
            mutation updateSourceFolder($sourceFolder: String!, $libraryId: ID) {
                updateSourceFolder(
                  input: { sourceFolder: $sourceFolder, libraryId: $libraryId }
                ) {
                  sourceFolder
                }
            }
        """
        response = logged_in_api_client.post_graphql(mutation, {'sourceFolder': '/data/photos/','libraryId': str(db_setup['library'].id)})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['updateSourceFolder']['sourceFolder'] == db_setup['library'].paths.all()[0].path

    def test_change_password_mutation(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(mutation, {'oldPassword': db_setup['password'],'newPassword': 'download123'})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['changePassword']['ok']

    def test_after_signup_api(self, logged_in_api_client, db_setup):
        query = """
            {
              afterSignup {
                token
                refreshToken
              }
            }
        """
        response = logged_in_api_client.post_graphql(query)
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['afterSignup']['token']
        assert data['data']['afterSignup']['refreshToken']

    def test_photo_rating_mutation(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(mutation, {'photoId': str(db_setup['snow_photo'].id),'starRating':4})
        data = get_graphql_content(response)
        assert response.status_code == 200
        assert data['data']['photoRating']['photo']['starRating'] == 4
        assert data['data']['photoRating']['photo']['aperture'] == db_setup['snow_photo'].aperture

    def test_create_generic_tag_mutation(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(
            mutation, {'name': 'snow-photo', 'photoId': str(db_setup['snow_photo'].id)})
        data = get_graphql_content(response)
        created_generic_tag_obj = Tag.objects.get(name='snow-photo')
        assert data['data']['createGenericTag']['ok']
        assert data['data']['createGenericTag']['photoTagId'] == str(created_generic_tag_obj.photo_tags.all()[0].id)
        assert data['data']['createGenericTag']['tagId'] == str(created_generic_tag_obj.id)
        assert data['data']['createGenericTag']['name'] == 'snow-photo'

    def test_remove_generic_tag_mutation(self, logged_in_api_client, db_setup):
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
        response = logged_in_api_client.post_graphql(
            mutation, {'name': 'snow-photo', 'photoId': str(db_setup['snow_photo'].id)})
        data = get_graphql_content(response)
        created_generic_tag_obj = Tag.objects.get(name='snow-photo')
        assert data['data']['createGenericTag']['ok']

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
        response = logged_in_api_client.post_graphql(
            mutation, {'tagId': str(created_generic_tag_obj.id), 'photoId': str(db_setup['snow_photo'].id)})
        data = get_graphql_content(response)
        assert data['data']['removeGenericTag']['ok']
        assert not Photo.objects.get(id=db_setup['snow_photo'].id).photo_tags.filter(id=created_generic_tag_obj.id).exists()
        assert not Tag.objects.filter(id=created_generic_tag_obj.id).exists()

    def test_get_photo_detail_api(self, logged_in_api_client, db_setup):
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
        tree_tag, _ = Tag.objects.get_or_create(library=db_setup['library'], name='Tree', type='O')
        tree_photo_tag, _ = PhotoTag.objects.get_or_create(photo=db_setup['tree_photo'], tag=tree_tag, confidence=1.0)
        response = logged_in_api_client.post_graphql(query, {'id': str(db_setup['tree_photo'].id)})
        assert response.status_code == 200
        data = get_graphql_content(response)
        photo_data = data['data']['photo']
        assert photo_data['id'] == str(db_setup['tree_photo'].id)
        assert photo_data['aperture'] == db_setup['tree_photo'].aperture
        assert photo_data['exposure'] == db_setup['tree_photo'].exposure
        assert photo_data['isoSpeed'] == db_setup['tree_photo'].iso_speed
        assert str(photo_data['focalLength']) == str(db_setup['tree_photo'].focal_length)
        assert photo_data['meteringMode'] == db_setup['tree_photo'].metering_mode
        assert not photo_data['flash']
        assert photo_data['camera']['id'] == str(db_setup['tree_photo'].camera.id)
        assert photo_data['width'] == db_setup['tree_photo'].dimensions[0]
        assert photo_data['height'] == db_setup['tree_photo'].dimensions[1]
        assert photo_data['objectTags'][0]['id'] == str(tree_photo_tag.id)
        assert photo_data['objectTags'][0]['tag']['name'] == tree_tag.name
        assert photo_data['url'].startswith('/thumbnails')

    def test_filter_photos_by_date_api(self, logged_in_api_client, db_setup):
        tree_tag, _ = Tag.objects.get_or_create(library=db_setup['library'], name='Tree', type='O')
        PhotoTag.objects.get_or_create(photo=db_setup['tree_photo'], tag=tree_tag, confidence=1.0)
        taken_at_date = db_setup['snow_photo'].taken_at
        multi_filter = 'library_id:{0} {1}'.format(db_setup['library'].id, taken_at_date.year)
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
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 2
        assert data['data']['allPhotos']['edges'][1]['node']['id'] == str(db_setup['snow_photo'].id)
        assert data['data']['allPhotos']['edges'][0]['node']['id'] == str(db_setup['tree_photo'].id)

        multi_filter = 'library_id:{0} {1} {2}'.format(db_setup['library'].id, taken_at_date.strftime('%B').lower(),taken_at_date.year)
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

        multi_filter = 'library_id:{0} {1} {2}'.format(db_setup['library'].id, taken_at_date.strftime('%b').lower(), taken_at_date.year)
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

        multi_filter = 'library_id:{0} {1} {2} {3}'.format(db_setup['library'].id, taken_at_date.strftime('%b').lower(), taken_at_date.strftime("%d"), taken_at_date.year)
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

        multi_filter = 'library_id:{0} {1} {2} {3}'.format(db_setup['library'].id, taken_at_date.strftime("%d"), taken_at_date.strftime('%b').lower(), taken_at_date.year)
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

        multi_filter = 'library_id:{0} party in {1} {2}'.format(db_setup['library'].id, taken_at_date.strftime('%b').lower(), taken_at_date.year)
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 0

        taken_at_date = db_setup['tree_photo'].taken_at
        multi_filter = 'library_id:{0} Tree in {1} {2}'.format(db_setup['library'].id, taken_at_date.strftime('%b').lower(), taken_at_date.year)
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

        multi_filter = 'library_id:{0} tag:{1} {2} {3}'.format(db_setup['library'].id, tree_tag.id, taken_at_date.strftime('%B').lower(), taken_at_date.year)
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allPhotos']['edges']) == 1

    def test_filter_photos_for_map_api(self, logged_in_api_client, db_setup):
        tree_tag, _ = Tag.objects.get_or_create(library=db_setup['library'], name='Tree', type='O')
        PhotoTag.objects.get_or_create(photo=db_setup['tree_photo'], tag=tree_tag, confidence=1.0)
        taken_at_date = db_setup['tree_photo'].taken_at
        multi_filter = 'library_id:{0} tag:{1} {2} {3}'.format(db_setup['library'].id, tree_tag.id, taken_at_date.strftime('%B').lower(),taken_at_date.year)
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
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['mapPhotos']['edges']) == 1
        assert data['data']['mapPhotos']['edges'][0]['node']['id'] == str(db_setup['tree_photo'].id)
        assert data['data']['mapPhotos']['edges'][0]['node']['url'].startswith('/thumbnails')
        assert data['data']['mapPhotos']['edges'][0]['node']['location']

    def test_filter_with_exposure_range_api(self, logged_in_api_client, db_setup):
        multi_filter = 'library_id:{0} exposure:1/4000-1/1600-1/1124-1/1000-1/800-1/500-1/400'.format(db_setup['library'].id)
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
        response = logged_in_api_client.post_graphql(query, {'filters': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['mapPhotos']['edges']) == 1

    def test_response_of_get_filters_api(self, logged_in_api_client, db_setup):
        object_type_tag, _ = Tag.objects.get_or_create(library=db_setup['library'], name='Tree', type='O')
        PhotoTag.objects.get_or_create(photo=db_setup['tree_photo'], tag=object_type_tag, confidence=1.0)
        color_type_tag, _ = Tag.objects.get_or_create(library=db_setup['library'], name='Yellow', type='C')
        PhotoTag.objects.get_or_create(photo=db_setup['tree_photo'], tag=color_type_tag, confidence=1.0)
        white_color_tag, _ = Tag.objects.get_or_create(library=db_setup['library'], name='White', type='C')
        PhotoTag.objects.get_or_create(photo=db_setup['snow_photo'], tag=white_color_tag, confidence=1.0)
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
        response = logged_in_api_client.post_graphql(query, {'libraryId': str(db_setup['library'].id),'multiFilter': multi_filter})
        data = get_graphql_content(response)
        assert len(data['data']['allObjectTags']) == 1
        assert data['data']['allObjectTags'][0]['name'] == object_type_tag.name
        assert len(data['data']['allColorTags']) == 2
        assert data['data']['allColorTags'][0]['name'] == white_color_tag.name
        assert data['data']['allColorTags'][1]['name'] == color_type_tag.name
        assert data['data']['allApertures'][0] == db_setup['tree_photo'].aperture
        assert data['data']['allCameras'][0]['id'] == str(db_setup['snow_photo'].camera.id)
        assert str(data['data']['allFocalLengths'][0]) == str(db_setup['snow_photo'].focal_length)


@pytest.mark.django_db
class TestGraphQLOnboarding:
    """Check onboarding(user sign up) process queries."""

    def test_onboarding_steps(self, api_client):
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
