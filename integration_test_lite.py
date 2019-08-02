import asyncio
import json
import sys
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

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo):
        await self.session.close()

    async def set_access_token(self):
        """Helper function to set the access token"""
        session = self.session
        config_json = self.config_json
        post_data = {
            'client_id': config_json["client_id"],
            'client_secret': config_json["client_secret"],
            'grant_type': 'client_credentials'
        }

        request = await session.post(config_json["token_api"], data=post_data)
        response = await request.json()
        self.access_token = f'Bearer {response["access_token"]}'

    def basic_request(self, url, params, needs_access_token, verb="get"):
        """Basic http request with url and query parameters

        :param str url: Request url
        :param dict params: Request params
        :param bool needs_access_token: True if request required an access
                                        token
        :param str verb: HTTP request verb
        """
        session = self.session

        headers = {}
        if (needs_access_token):
            headers['Authorization'] = self.access_token

        request = session.request(verb, url, params=params, headers=headers)
        return request

    async def bad_response(self, endpoint):
        """Tests an endpoint for an unexpected response

        :param dict endpoint: The endpoint object from the config file
        :returns: None if the response was ok. Otherwise, an error object
        :rtype: dict
        """
        query_params = endpoint["query_params"]
        # Add random query parameter with random value to bypass caching
        query_params[uuid.uuid4().hex] = uuid.uuid4().hex

        request = await self.basic_request(
            endpoint["base_url"],
            query_params,
            endpoint["needs_access_token"]
        )
        response_code = request.status

        allowed_response_codes = [200]
        if 'allow_400' in endpoint and endpoint['allow_400']:
            allowed_response_codes.append(400)

        if response_code not in allowed_response_codes:
            api_info = endpoint
            api_info["response_code"] = response_code

            try:
                api_info["response_body"] = await request.json()
            except ValueError as error:
                api_info["response_body"] = str(error)
            return api_info

    async def get_bad_apis(self):
        """Tests all endpoints and returns a list of errors

        :returns: List of errors
        :rtype: list
        """
        endpoints = self.config_json['target_endpoints']

        # Execute all tests in parallel
        results = await asyncio.gather(
            *[self.bad_response(endpoint) for endpoint in endpoints]
        )
        # Return all results that weren't None
        return [result for result in results if result]


async def main():
    async with IntegrationTestLite() as integration_test_lite:
        await integration_test_lite.set_access_token()
        bad_apis = await integration_test_lite.get_bad_apis()

        if len(bad_apis) > 0:
            print("The following API(s) returned errors:")
            pretty_print(bad_apis)
            sys.exit(1)

asyncio.run(main())
