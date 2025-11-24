import json
from unittest import mock

import fakeredis
import pytest

import photonix.photos.utils.redis


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """
    Patches photonix.photos.utils.redis.redis_connection with a FakeRedis instance
    for ALL tests.
    """
    server = fakeredis.FakeServer()
    fake_conn = fakeredis.FakeStrictRedis(server=server, version=6)

    # Patch the global redis_connection object in the module
    monkeypatch.setattr(photonix.photos.utils.redis,
                        'redis_connection', fake_conn)

    return fake_conn


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    class GraphQLClient(APIClient):
        def post_graphql(self, query, variables=None):
            data = {'query': query}
            if variables:
                data['variables'] = variables
            return self.post('/graphql', data=data, format='json')

    return GraphQLClient()
