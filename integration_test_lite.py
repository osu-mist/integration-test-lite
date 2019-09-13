import asyncio
from datetime import date
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
        self.session = aiohttp.ClientSession()

        self.textbooks_api_config_helper()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo):
        await self.session.close()

    def textbooks_api_config_helper(self):
        """Modifies any textbook API endpoints to use the current term and
        academic year so a valid query can be made"""

        term_months = {
            'Winter': [12, 1, 2],
            'Spring': [3, 4, 5],
            'Summer': [6, 7, 8],
            'Fall': [9, 10, 11],
        }
        today = date.today()
        academic_year = str(today.year)
        term = None
        for key, val in term_months.items():
            if today.month in val:
                term = key
                break

        textbooks_url_regex = r'.*/textbooks'
        textbook_endpoints = list(filter(
            lambda x: re.match(textbooks_url_regex, x['base_url']),
            self.config_json['target_endpoints']
        ))
        for endpoint in textbook_endpoints:
            endpoint['query_params']['academicYear'] = academic_year
            endpoint['query_params']['term'] = term

    async def set_access_token(self):
        """Helper function to set the access token"""
        session = self.session
        config_json = self.config_json
        post_data = {
            'client_id': config_json['client_id'],
            'client_secret': config_json['client_secret'],
            'grant_type': 'client_credentials'
        }

        response = await session.post(config_json['token_api'], data=post_data)
        response_body = await response.json()
        self.access_token = f"Bearer {response_body['access_token']}"

    def basic_request(self, url, params, needs_access_token, method='get'):
        """Basic http request with url and query parameters

        :param str url: Request url
        :param dict params: Request params
        :param bool needs_access_token: True if request required an access
                                        token
        :param str method: HTTP request method
        :returns: An awaitable HTTP response
        """
        session = self.session

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
        response = await self.basic_request(
            url,
            query_params,
            endpoint['needs_access_token']
        )
        response_code = response.status

        if response_code != 200:
            api_info = endpoint
            api_info['response_code'] = response_code

            try:
                api_info['response_body'] = await response.json()
            except Exception as error:
                api_info['response_body'] = {
                    'raw': await response.text(),
                    'error': str(error)
                }
            return api_info
        else:
            query_param_string = urlencode(query_params)
            print(f'    [{response_code}] {url}?{query_param_string}')

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
        print()
        # Return all results that weren't None
        return [result for result in results if result]


async def main():
    async with IntegrationTestLite() as integration_test_lite:
        await integration_test_lite.set_access_token()
        bad_apis = await integration_test_lite.get_bad_apis()

        if bad_apis:
            print('The following API(s) returned errors:')
            pretty_print(bad_apis)
            sys.exit(1)

asyncio.run(main())
