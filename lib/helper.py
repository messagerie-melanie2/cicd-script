from lib.global_vars import *

logger = logging.getLogger(__name__)

def request(mode, url = '', headers = None, auth = None, payload_data = None, payload_json = None, files = None, params = None):
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
        files (dict): Data sent as JSON using the `files` parameter.
        params (dict): Data sent as JSON using the `params` parameter.

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
                r = requests.get(url=url, headers=headers, auth=auth, data=payload_data, json = payload_json, files=files, params=params)
            case "post":
                r = requests.post(url=url, headers=headers, auth=auth, data=payload_data, json = payload_json, files=files, params=params)
            case "put":
                r = requests.put(url=url, headers=headers, auth=auth, data=payload_data, json = payload_json, files=files, params=params)
            case "patch":
                r = requests.patch(url=url, headers=headers, auth=auth, data=payload_data, json = payload_json, files=files, params=params)
            case "delete":
                r = requests.delete(url=url, headers=headers, auth=auth, data=payload_data, json = payload_json, files=files, params=params)
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

def get_changes(changes_info_file):
    """
    Creating a list of changes by reading a file.

    Args:
        changes_info_file (str): Path of change info file.

    Returns:
        changes (str): Changed files between two commit.
    """
    #Create an array with the files changed during commit
    changes = []
    try:
        # Read changes.txt
        changes_file = open(changes_info_file, 'r')

    except OSError as err:
        logging.debug(f"changes.txt not found... Error : {err}")
        changes_file = []
    
    for line in changes_file :
        changes.append(line) 
        # changes = ["/debian/3.4/Dockerfile",...]

    return changes 

def get_user_id(assignee_username, project_user, multiple_user) :
    """
    Get users ids depending of their username.

    Args:
        issue (dict): The issue json.
        project_user (list): List of all user of the project
        multiple_user (bool): Permit multiple user feature.

    Returns:
        user_id (list): List of all user ids needed.
    """

    user_id = []
    if assignee_username != None :
        assignee_username = assignee_username.lower().split(",")
        logger.debug(f"assignee_username: {assignee_username}")
        if len(assignee_username) > 1  and not multiple_user:
            logger.error(f"assignee_username must have only one username because multiple user is false")
            sys.exit()
        for user in project_user :
            if user.get("username").lower() in assignee_username :
                user_id.append(user.get("id"))
                logger.info(f"User {user.get("username")} found with id : {user.get("id")}")
    
    logger.debug(f"user_id: {user_id}")
    if len(user_id) == 0 : 
        logger.warning(f"No user found with name : {assignee_username}")

    return user_id 