# coding=utf-8
from lib.global_vars import *
from lib.helper import request

logger = logging.getLogger(__name__)
#=======================================================#
#============== Gitlab Tools Functions =================#
#=======================================================#
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

        url = f"{GITLAB_URL}api/v4/groups/{group_id}/projects?per_page=100&page={i+1}"
        r = request("get", url, headers)
        if r != {} :
            projects += r
            i += 1
        else : 
            stop = True
    
    return(projects)

def get_registry_info(token, project_id = 0):
    """
    Retrieve all registry repositories for a GitLab project, handling pagination.

    This function queries the GitLab API for the repositories belonging to the
    project registry identified by `project_id`. The GitLab API returns a maximum of 100
    projects per page, so this function requests pages repeatedly and
    concatenates the results until there are no more projects to fetch.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query. Defaults to 0.

    Returns:
        registry (list): A list of repositories dictionaries as returned by the GitLab API.
    """
    headers = {"PRIVATE-TOKEN": token}
    registry = []
    i = 0
    error = False

    #Max per page is only 100 so we have to loop to get all repositories
    while len(registry) == 100*i  and not error:
        url = f"{GITLAB_URL}api/v4/projects/{project_id}/registry/repositories?per_page=100&page={i+1}"
        response = request("get", url, headers)
        if response == {} :
            error = True
        else :
            registry += response
            i += 1
    
    logger.debug(f"Registry_info : {registry}")
    
    return(registry)

def get_repository_id(registry,df_name):
    """
    Retrieve the registry repository id based on his name.

    Args:
        registry (list): A list of repositories dictionaries as returned by the GitLab API.
        df_name (str): Registry repository name.

    Returns:
        repository_id (int): Registry repository ID.
    """

    repository_id = -1 

    for repository in registry :
        if repository["name"] == df_name :
            repository_id = repository["id"]
    
    logger.debug(f"{df_name} repository id : {repository_id}")

    return repository_id

def get_tags_in_repository(token,project_id,repository_id):
    """
    Retrieve all tags of a registry project repository.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query.
        repository_id (int): Registry repository ID.

    Returns:
        tags (list): A list of tags dictionaries as returned by the GitLab API.
    """

    tags = []
    headers = {"PRIVATE-TOKEN": token}
    url = f"{GITLAB_URL}api/v4/projects/{project_id}/registry/repositories/{repository_id}/tags?per_page=100"
    tags = request("get", url, headers)
    
    return tags

def find_tag_in_repository(token,project_id,repository_id,tag_target):
    """
    Check if a specific tag exist in a registry project repository.

    Get all tags of a registry project repository and find a specific one based on tag_target argument.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query.
        repository_id (int): Registry repository ID.
        tag_target (str): Tag name to find.

    Returns:
        bool (bool): True if tag is in registry repository and False if else.
    """

    tags = get_tags_in_repository(token,project_id,repository_id)

    for tag in tags :
        if tag["name"] == tag_target :
            return True
    
    return False

def get_branches(token,project_id):
    """
    Retrieve branchs of a project repository.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query.

    Returns:
        branches (list): A list of branches dictionaries as returned by the GitLab API.
    """

    branches = []
    headers = {"PRIVATE-TOKEN": token}
    url = f"{GITLAB_URL}api/v4/projects/{project_id}/repository/branches?per_page=100"
    branches = request("get", url, headers)
    
    return branches

def get_users(token,project_id):
    """
    Retrieve users of a project.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query.

    Returns:
        users (list): A list of users dictionaries as returned by the GitLab API.
    """

    users = []
    headers = {"PRIVATE-TOKEN": token}
    url = f"{GITLAB_URL}api/v4/projects/{project_id}/users?per_page=100"

    logger.info(f"Get users for {project_id} project")
    users = request("get", url, headers)
    logger.debug(f"users : {users}")
    
    return users

def get_issues(token,project_id, issue_filter):
    """
    Create an issue for a project.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query.
        issue_payload (dict): Issues information to create

    Returns:
        users (list): A list of users dictionaries as returned by the GitLab API.
    """

    issues = {}
    headers = {"PRIVATE-TOKEN": token}

    url = f"{GITLAB_URL}api/v4/projects/{project_id}/issues"
    logger.info(f"Get issues for {project_id} project with filter : {issue_filter}")
    issues = request("get", url, headers, payload_data=issue_filter)
    logger.debug(f"issues : {issues}")

    return issues

def create_issue(token,project_id, issue_payload):
    """
    Create an issue for a project.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query.
        issue_payload (dict): Issues information to create

    Returns:
        users (list): A list of users dictionaries as returned by the GitLab API.
    """

    issue = {}
    headers = {"PRIVATE-TOKEN": token}

    url = f"{GITLAB_URL}api/v4/projects/{project_id}/issues"
    logger.info(f"Create issue ({issue_payload}) for {project_id} project")
    issue = request("post", url, headers, payload_data=issue_payload)
    logger.debug(f"issue : {issue}")

    return issue

def create_issue_link(token, issue, issue_target):
    """
    Create an issue for a project.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query.
        issue_payload (dict): Issues information to create

    Returns:
        users (list): A list of users dictionaries as returned by the GitLab API.
    """
    headers = {"PRIVATE-TOKEN": token}
    new_issue_link = {}

    url = f'{GITLAB_URL}api/v4/projects/{issue["project_id"]}/issues/{issue["iid"]}/links'
    params = {
        'target_project_id': issue_target["project_id"],
        'target_issue_iid': issue_target["iid"],
    }

    logger.info(f"Create issue link between ({issue}) and ({issue_target})")
    new_issue_link = request("post", url, headers, params=params)
    logger.debug(f"new_issue_link : {new_issue_link}")
    
    return new_issue_link

#DELETE

def delete_repository_in_registry(token,project_id,repository_id):
    """
    Delete a given registry repository.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query.
        repository_id (int): Registry repository ID.

    Returns:
        deleted (bool): True if deleted.
    """

    deleted = False
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/registry/repositories/'+str(repository_id)
    response = request("delete", url, headers)

    if response != {} :
        deleted = True
    
    return deleted

def delete_tag_in_repository(token,project_id,repository_id,tag_name):
    """
    Delete a given tag in a registry repository.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query.
        repository_id (int): Registry repository ID.
        tag_name (str): Tag name to delete.

    Returns:
        deleted (bool): True if deleted.
    """

    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/registry/repositories/'+str(repository_id)+'/tags/'+str(tag_name)
    deleted = False
    logging.debug(f"Url : {url}")
    response = request("delete", url, headers)

    if response != {} :
        deleted = True
    
    return deleted