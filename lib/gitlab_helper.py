# coding=utf-8
from global_vars import *
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

        url = GITLAB_URL + 'api/v4/groups/'+str(group_id)+'/projects?per_page=100&page='+str(i+1)
        r = request("get", url, headers)
        if r != {} :
            projects += r
            i += 1
        else : 
            stop = True
    
    return(projects)

def get_registry_info(token, project_id = 0):

    headers = {"PRIVATE-TOKEN": token}
    registry = []
    i = 0
    error = False

    #Max per page is only 100 so we have to loop to get all repositories
    while len(registry) == 100*i  and not error:
        url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/registry/repositories?per_page=100&page='+str(i+1)
        response = request("get", url, headers)
        if response == {} :
            error = True
        else :
            registry += response
            i += 1
    
    logger.debug(f"Registry_info : {registry}")
    
    return(registry)

def get_repository_id(registry,df_name):
    
    repository_id = -1 

    for repository in registry :
        if repository["name"] == df_name :
            repository_id = repository["id"]
    
    logger.debug(f"{df_name} repository id : {repository_id}")

    return repository_id

def get_tags_in_repository(token,project_id,repository_id):
    tags = []
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/registry/repositories/'+str(repository_id)+'/tags?per_page=100'
    tags = request("get", url, headers)
    
    return tags

def find_tag_in_repository(token,project_id,repository_id,tag_target):

    tags = get_tags_in_repository(token,project_id,repository_id)

    for tag in tags :
        if tag["name"] == tag_target :
            return True
    
    return False

def get_branches(token,project_id):
    branches = []
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/repository/branches?per_page=100'
    branches = request("get", url, headers)
    
    return branches

#DELETE

def delete_repository_in_registry(token,project_id,repository_id):
    deleted = False
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/registry/repositories/'+str(repository_id)
    response = request("delete", url, headers)

    if response != {} :
        deleted = True
    
    return deleted

def delete_tag_in_repository(token,project_id,repository_id,tag_name):
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/registry/repositories/'+str(repository_id)+'/tags/'+str(tag_name)
    deleted = False
    logging.debug(f"Url : {url}")
    response = request("delete", url, headers)

    if response != {} :
        deleted = True
    
    return deleted