import asyncio
import json
import sys
import uuid

import aiohttp


# Helper function to pretty print a list or dictionary
def pretty_print(print_me):
    print(json.dumps(print_me, indent=4, sort_keys=True))


class IntegrationTestLite:
    def __init__(self):
        config_data_file = open(sys.argv[1])
        self.config_json = json.load(config_data_file)

        # TODO remove
        self.config_json['target_endpoints'] = (
            self.config_json['target_endpoints'] * 10
        )

        self.session = aiohttp.ClientSession()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo):
        await self.session.close()

    # Helper function to set the access token
    async def set_access_token(self):
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

    # Basic http request with url and query parameters
    def basic_request(self, url, params, needs_access_token, verb="get"):
        session = self.session

        headers = {}
        if (needs_access_token):
            headers['Authorization'] = self.access_token

        request = session.request(verb, url, params=params, headers=headers)
        return request

    # Makes a call to each API and adds the API
    # to a list if the call wasn't successful
    async def get_bad_apis(self):
        bad_apis = []

        async def test_endpoint(endpoint):
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

                bad_apis.append(api_info)
                # request.close()

        tasks = []
        for endpoint in self.config_json["target_endpoints"]:
            tasks.append(test_endpoint(endpoint))

        await asyncio.gather(*tasks)

        return bad_apis


async def main():
    async with IntegrationTestLite() as integration_test_lite:
        await integration_test_lite.set_access_token()
        bad_apis = await integration_test_lite.get_bad_apis()

    if len(bad_apis) > 0:
        print("The following API(s) returned errors:")
        pretty_print(bad_apis)
        sys.exit(1)

asyncio.run(main())
