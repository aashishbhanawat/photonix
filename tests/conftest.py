import pytest
import json

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
