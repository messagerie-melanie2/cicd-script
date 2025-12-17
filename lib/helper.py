from lib.global_vars import *

logger = logging.getLogger(__name__)

def request(mode, url = '', headers = None, auth = None, payload_data = None, payload_json = None, files = None):
    """
    Sends an HTTP request based on the specified mode.

    This function wraps common HTTP methods (`GET`, `POST`, `PUT`, `PATCH`)
    from the `requests` library. It also handles HTTP errors and can display
    debug information when needed.

    Args:
        mode (str): The HTTP method to use. Must be one of
            {"get", "post", "put", "patch"}.
        url (str): The target URL for the request. Defaults to ''.
        headers (dict): HTTP headers to include in the request.
        payload_data (dict or bytes): Data sent using the `data` parameter.
        payload_json (dict): Data sent as JSON using the `json` parameter.
        files (dict): Files to upload using multipart/form-data.

    Returns:
        response (dict): The JSON response content if the request succeeds.

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
                r = requests.post(url=url, headers=headers, auth=auth, data=payload_data, json = payload_json, files=files)
            case "put":
                r = requests.put(url=url, headers=headers, auth=auth, data=payload_data, json = payload_json, files=files)
            case "patch":
                r = requests.patch(url=url, headers=headers, auth=auth, data=payload_data, json = payload_json, files=files)
            case _:
                logger.warning(f"request mode {mode} not supported")
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.error(f"Request failed : {r.json()}")
        logger.debug(f"Http Error: {err}")
    else :
        if r.status_code in ACCEPTED_STATUS_CODE:
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

def add_argument_to_conf(project, arguments_dict, type) :
    """
    Builds a dictionary of arguments based on a dictionary (format: {'type1': 'argument1,argument2','type2': 'argument3'}) settings.

    Args:
        project (dict): The project configuration dictionary.
        type (str): The trigger argument category to extract.

    Returns:
        configuration_to_add (dict): A dictionary containing the trigger arguments relevant to the given type.
    """
    configuration_to_add = {}
    argument_list = arguments_dict[type].split(',')

    for argument in argument_list :
        value = project.get(argument)
        if value != None :
            logging.debug(f"Adding {argument} to configuration.")
            configuration_to_add[argument] = value
    
    return configuration_to_add

def set_new_ci_variable(url, headers, project_id, project_variables, variable_payload) :
    """
    Creates or updates a CI/CD variable for a specific GitLab project.

    If the variable already exists, it is updated. Otherwise, a new variable
    is created.

    Args:
        url (str): the url to request
        headers (dict): HTTP headers including the GitLab access token.
        project_id (int): The ID of the project where variables are defined.
        project_variables (list): Existing variables retrieved from the GitLab API.
        variable_payload (dict): Payload to create the variable (format: {'key': 'mykey','value':'value'}).

    Returns:
        variable_already_put (bool): True if the variable already existed, False if it was newly created.
    """
    variable_already_put = False
    variable_key = variable_payload.get("key")
    variable_value = variable_payload.get("value")

    for variable in project_variables :
        if variable.get("key") == variable_key :
            variable_already_put = True
    
    if variable_already_put :
        url = f"{url}/{variable_key}?value={variable_value}"
        request("put", url, headers)
    else :
        logger.info(f"Setup {variable_key} for {project_id} project")
        request("post", url, headers, payload_data=variable_payload)

    return variable_already_put

def enable_allowlist(token, project):
    """
    Enable the job token allowlist for a GitLab project.

    Args:
        token (str): Private token used for authentication.
        project (dict): Dictionary representing the project.

    Returns:
        None
    """
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get("name")
    project_id = project.get("id")

    logger.info(f"Enabling allowlists of {project_name} project...")
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope"
    payload = {'enabled': True}
    request("patch",url, headers, payload_data=payload)

def get_allowlist(token, project, allowlist_type = 'project'):
    """
    Getting the job token allowlist for a GitLab project.

    Args:
        token (str): Private token used for authentication.
        project (dict): Dictionary representing the project.
        allowlist_type (str): Indicate if we want group allowlist or project allowlist

    Returns:
        None
    """
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get("name")
    project_id = project.get("id")

    logger.info(f"Getting allowlists of {project_name} project...")
    
    suffix = "allowlist?per_page=100"
    if allowlist_type == 'group' :
        suffix = f"groups_{suffix}"

    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope/{suffix}"
    project_allowlist = request("get", url, headers)
    logger.debug(f"project_allowlist : {project_allowlist}")

    return project_allowlist

def set_new_allowlist(url, headers, project_allowlist, allowlist_payload, instance_to_allow_id) :
    """
    Adds a project to a GitLab job token allowlist if it is not already included.

    Args:
        headers (dict): HTTP headers containing the GitLab authentication token.
        project_allowlist (list): List of projects currently in the allowlist.
        allowlist_payload (dict): Payload to create allowlist.
        project_to_allow_id (int): The ID of the project to add to the allowlist.

    Returns:
        None
    """
    project_allowlist_already_setup = False

    for project in project_allowlist :
        if project.get("id") == instance_to_allow_id :
            project_allowlist_already_setup = True

    if not project_allowlist_already_setup :
        request("post",url, headers, payload_data=allowlist_payload)
    else : 
        logger.info("Already added to allowlist.")

def get_project_info(token, project) :
    """
    Retrieve detailed information for a GitLab project.

    Args:
        token (str): Private access token for the GitLab API.
        project (dict): The project configuration dictionary.

    Returns:
        project_info (dict): Parsed JSON response containing project information.

    """
    
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get("name")
    project_id = project.get("id")

    url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
    logger.info(f"Getting {project_name} project info...")
    project_info = request("get", url, headers)
    logger.debug(f"project_info : {project_info}")

    return project_info

def get_groups_project(token, group_id = 0):
    """
    Retrieve all projects for a GitLab group, handling pagination.

    This function queries the GitLab API for the projects belonging to the
    group identified by `group_id`. The GitLab API returns a maximum of 100
    projects per page, so this function requests pages repeatedly and
    concatenates the results until there are no more projects to fetch.

    Args:
        token (str): Private access token for the GitLab API.
        group_id (int): ID of the GitLab group to query. Defaults to 0.

    Returns:
        projects (list): A list of project dictionaries as returned by the GitLab API.
    """

    headers = {"PRIVATE-TOKEN": token}
    projects = []

    i = 0
    stop = False

    #Max per page is only 100 so we have to loop to get all projects
    while len(projects) == 100*i  and not stop:

        url = GITLAB_URL + 'api/v4/groups/'+str(group_id)+'/projects?per_page=100&page='+str(i+1)
        r = request("get", url, headers)
        if r != {} :
            projects += r
            i += 1
        else : 
            stop = True
    
    return(projects)