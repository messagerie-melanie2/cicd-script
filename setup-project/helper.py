from global_vars import *

logger = logging.getLogger(__name__)

def request(mode, url = '', headers = None, payload_data = None, payload_json = None, files = None):
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
                r = requests.get(url=url, headers=headers)
            case "post":
                r = requests.post(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case "put":
                r = requests.put(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case "patch":
                r = requests.patch(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case _:
                logger.warning(f"request mode {mode} not supported")
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.error(f"Request failed : {r.json()}")
        logger.debug(f"Http Error: {err}")
    else :
        if r.status_code in SETUP_ACCEPTED_STATUS_CODE:
            response = r.json()
    
    return response
    

def send_message(url, message):
    """
    Sends a message to the configured trigger channel endpoint.

    If `url` is defined, this function sends a POST
    request containing the message content.

    Args:
        url (str): the url to request
        message (str): The message to send.

    Returns:
        None
    """
    if url != "" :
        payload = {
            'message': message,
            'message_raw': message
        }
        request("post",url, payload_json=payload)

def set_new_ci_variable(headers, project_id, project_variables, variable_key, variable_value, variable_masked) :
    """
    Creates or updates a CI/CD variable for a specific GitLab project.

    If the variable already exists, it is updated. Otherwise, a new variable
    is created.

    Args:
        headers (dict): HTTP headers including the GitLab access token.
        project_id (int): The ID of the project where variables are defined.
        project_variables (list): Existing variables retrieved from the GitLab API.
        variable_key (str): The key/name of the variable.
        variable_value (str): The value to set for the variable.
        variable_masked (bool): Whether the variable should be masked in GitLab.

    Returns:
        bool: True if the variable already existed, False if it was newly created.
    """
    variable_already_put = False

    for variable in project_variables :
        if variable.get("key") == variable_key :
            variable_already_put = True
    
    if variable_already_put :
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables/{variable_key}?value={variable_value}"
        request("put", url, headers)
    else :
        logger.info(f"Setup %s{variable_key} for {project_id} project")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
        payload = {
            'key': variable_key,
            'value': variable_value,
            'masked': variable_masked,
        }
        request("post", url, headers, payload_data=payload)

    return variable_already_put

def set_new_allowlist(headers, project_allowlist, project_id, project_to_allow_id) :
    """
    Adds a project to a GitLab job token allowlist if it is not already included.

    Args:
        headers (dict): HTTP headers containing the GitLab authentication token.
        project_allowlist (list): List of projects currently in the allowlist.
        project_id (int): The ID of the project whose allowlist is being modified.
        project_to_allow_id (int): The ID of the project to add to the allowlist.

    Returns:
        None
    """
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope/allowlist"
    payload = {'target_project_id': project_to_allow_id}
    project_allowlist_already_setup = False

    for project in project_allowlist :
        if project.get("id") == project_to_allow_id :
            project_allowlist_already_setup = True

    if not project_allowlist_already_setup :
        request("post",url, headers, payload_data=payload)
    else : 
        logger.info("Already added to allowlist.")