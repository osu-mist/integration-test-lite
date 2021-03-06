import asyncio
import json
import re
import sys
from urllib.parse import urlencode
import uuid

import aiohttp


def pretty_print(print_me):
    """Helper function to pretty print a list or dictionary

    :param print_me: The list/dictionary to be printed
    """
    print(json.dumps(print_me, indent=4, sort_keys=True))


class IntegrationTestLite:
    def __init__(self):
        config_data_file = open(sys.argv[1])
        self.config_json = json.load(config_data_file)
        self.access_token = None
        self.total = self.config_json['request_timeout']
        self.timeout = aiohttp.ClientTimeout(total=self.total)

    def get_session(self):
        return aiohttp.ClientSession(timeout=self.timeout)

    async def set_access_token(self):
        """Helper function to set the access token"""
        config_json = self.config_json
        post_data = {
            'client_id': config_json['client_id'],
            'client_secret': config_json['client_secret'],
            'grant_type': 'client_credentials'
        }

        async with self.get_session() as session:
            async with (
                session.post(config_json['token_api'], data=post_data)
            ) as response:
                response_body = await response.json()
                self.access_token = f"Bearer {response_body['access_token']}"

    def basic_request(
            self,
            session,
            url,
            params,
            needs_access_token,
            method='get'
    ):
        """Basic http request with url and query parameters

        :param session aiohttp.ClientSession: Session for making request
        :param str url: Request url
        :param dict params: Request params
        :param bool needs_access_token: True if request required an access
                                        token
        :param str method: HTTP request method
        :returns: An awaitable HTTP response
        """
        headers = {}
        if needs_access_token:
            headers['Authorization'] = self.access_token

        return session.request(method, url, params=params, headers=headers)

    async def bad_response(self, endpoint):
        """Tests an endpoint for an unexpected response

        :param dict endpoint: The endpoint object from the config file
        :returns: None if the response was ok. Otherwise, an error object
        :rtype: dict
        """
        query_params = endpoint['query_params']
        # Add random query parameter with random value to bypass caching
        query_params[uuid.uuid4().hex] = uuid.uuid4().hex

        url = endpoint['base_url']
        api_info = endpoint

        # Handle textbooks api request
        textbooks_url_regex = r'.*/textbooks'
        if re.match(textbooks_url_regex, url):
            try:
                terms_url = 'https://osu.verbacompare.com/compare/courses'
                async with self.get_session() as session:
                    async with self.basic_request(
                        session,
                        terms_url,
                        {},
                        False
                    ) as terms_response:
                        terms_json = await terms_response.json()
                        query_params['academicYear'], query_params['term'] = (
                            terms_json[0]['id'].split('-')
                        )
            except Exception as error:
                api_info['error'] = (
                    'Exception when querying textbooks terms: '
                    f'{error.__class__.__name__}'
                )
                if str(error):
                    api_info['error'] += f': {str(error)}'
                return api_info

        try:
            async with self.get_session() as session:
                async with self.basic_request(
                    session,
                    url,
                    query_params,
                    endpoint['needs_access_token']
                ) as response:

                    response_code = response.status
                    if response_code != 200:
                        api_info['response_code'] = response_code

                        try:
                            api_info['response_body'] = await response.json()
                        except Exception as error:
                            api_info['response_body'] = {
                                'raw': await response.text(),
                                'error': str(error)
                            }
                        return api_info
                    query_param_string = urlencode(query_params)
                    print(f'    [{response_code}] {url}?{query_param_string}')

        except asyncio.TimeoutError:
            api_info['error'] = f'Timed out after {self.total} second(s)'
            return api_info

    async def get_bad_apis(self):
        """Tests all endpoints and returns a list of errors

        :returns: List of errors
        :rtype: list
        """
        endpoints = self.config_json['target_endpoints']

        print('Passing cases:')
        # Execute all tests in parallel
        results = await asyncio.gather(
            *[self.bad_response(endpoint) for endpoint in endpoints]
        )
        # Return all results that weren't None
        return [result for result in results if result]


async def main():
    integration_test_lite = IntegrationTestLite()
    await integration_test_lite.set_access_token()
    bad_apis = await integration_test_lite.get_bad_apis()

    if bad_apis:
        print('\nThe following API(s) returned errors:')
        pretty_print(bad_apis)
        sys.exit(1)

asyncio.run(main())
