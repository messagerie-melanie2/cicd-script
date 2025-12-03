from global_vars import *

def request(mode, url = '', headers = None, payload_data = None, payload_json = None, files = None , debug = False):
    """
    Sends an HTTP request based on the specified mode.

    This function wraps common HTTP methods (`GET`, `POST`, `PUT`, `PATCH`)
    from the `requests` library. It also handles HTTP errors and can display
    debug information when needed.

    Args:
        mode (str): The HTTP method to use. Must be one of
            {"get", "post", "put", "patch"}.
        url (str, optional): The target URL for the request. Defaults to ''.
        headers (dict, optional): HTTP headers to include in the request.
        payload_data (dict or bytes, optional): Data sent using the `data` parameter.
        payload_json (dict, optional): Data sent as JSON using the `json` parameter.
        files (dict, optional): Files to upload using multipart/form-data.
        debug (bool, optional): Whether to print debug information. Defaults to False.

    Returns:
        dict: The JSON response content if the request succeeds.

    Raises:
        requests.exceptions.HTTPError: If the server returns an HTTP error status.
    """
    response = {}
    try :
        r = requests.Response()
        match mode:
            case "get":
                r = requests.get(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case "post":
                r = requests.post(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case "put":
                r = requests.put(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case "patch":
                r = requests.patch(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case _:
                print("request mode not supported")  
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if debug : 
            print("Http Error:",err)
        print(f"Request failed : {r.json()}")
    else :
        if r.status_code == 200:
            response = r.json()
    
    return response
    

def send_message(url, message, debug = False):
    """
    Sends a message to the configured trigger channel endpoint.

    If `url` is defined, this function sends a POST
    request containing the message content.

    Args:
        url (str): the url to request
        message (str): The message to send.
        debug (bool, optional): Whether to print debug information. Defaults to False.

    Returns:
        None
    """
    if url != "" :
        payload = {
            'message': message,
            'message_raw': message
        }
        request("post",url, payload_json=payload, debug=debug)