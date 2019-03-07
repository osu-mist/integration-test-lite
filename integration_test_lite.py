import requests
import json
import sys
import uuid


# Helper function to pretty print a list or dictionary
def pretty_print(print_me):
    print(json.dumps(print_me, indent=4, sort_keys=True))


# Helper function to get an access token
def get_access_token():
    post_data = {
        'client_id': config_json["client_id"],
        'client_secret': config_json["client_secret"],
        'grant_type': 'client_credentials'
    }
    request = requests.post(config_json["token_api"], data=post_data)

    return f'Bearer {request.json()["access_token"]}'


# Basic http request with url and query parameters
def basic_request(url, params, needs_access_token, verb="get"):
    headers = {}

    if (needs_access_token):
        headers['Authorization'] = access_token

    request = requests.request(verb, url, params=params, headers=headers)
    return request


# Makes a call to each API and adds the API
# to a list if the call wasn't successful
def get_bad_apis():
    bad_apis = []

    for endpoint in config_json["target_endpoints"]:
        query_params = endpoint["query_params"]
        # Add random query parameter with random value to bypass caching
        query_params[uuid.uuid4().hex] = uuid.uuid4().hex

        request = basic_request(
            endpoint["base_url"], query_params, endpoint["needs_access_token"])
        response_code = request.status_code

        allowed_response_codes = [200]
        if 'allow_400' in endpoint and endpoint['allow_400']:
            allowed_response_codes.append(400)

        if response_code not in allowed_response_codes:
            api_info = endpoint
            api_info["response_code"] = response_code

            try:
                api_info["response_body"] = request.json()
            except ValueError as error:
                api_info["response_body"] = str(error)

            bad_apis.append(api_info)

    return bad_apis


if __name__ == '__main__':
    config_data_file = open(sys.argv[1])
    config_json = json.load(config_data_file)

    access_token = get_access_token()
    bad_apis = get_bad_apis()

    if len(bad_apis) > 0:
        print("The following API(s) returned errors:")
        pretty_print(bad_apis)
        sys.exit(1)
