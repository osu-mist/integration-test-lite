import requests, json, sys, uuid

# Helper function to pretty print a list or dictionary
def pretty_print(print_me):
    print json.dumps(print_me, indent=4, sort_keys=True)

# Helper function to get an access token
def get_access_token():
    post_data = {'client_id': config_json["client_id"],
         'client_secret': config_json["client_secret"],
         'grant_type': 'client_credentials'}
    request = requests.post(config_json["token_api"], data=post_data)

    return 'Bearer ' + request.json()["access_token"]

# Basic http request with url and query parameters
def basic_request(url, params, verb="get"):
    headers = {'Authorization': access_token}
    request = requests.request(verb, url, params=params, headers=headers)
    return request

# Makes a call to each API and adds the API to a list if the call wasn't successful
def get_bad_apis():
    bad_apis = []

    for endpoint in config_json["target_endpoints"]:
        query_params = endpoint["query_params"]
        query_params[uuid.uuid4().hex] = uuid.uuid4().hex

        request = basic_request(endpoint["base_url"], query_params)
        response_code = request.status_code
        
        if response_code is not 200:
            api_info = endpoint
            api_info["response_code"] = response_code
            api_info["response_body"] = request.json()
            bad_apis.append(api_info)

    return bad_apis

if __name__ == '__main__':
    options_tpl = ('-i', 'config_path')
    del_list = []

    for i,config_path in enumerate(sys.argv):
        if config_path in options_tpl:
            del_list.append(i)
            del_list.append(i+1)

    del_list.reverse()

    for i in del_list:
        del sys.argv[i]

    config_data_file = open(config_path)
    config_json = json.load(config_data_file)

    access_token = get_access_token()
    bad_apis = get_bad_apis()

    if len(bad_apis) > 0:
        print "The following API(s) returned errors:"
        pretty_print(bad_apis)
        sys.exit(1)
    