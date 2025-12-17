from setup.global_vars import *
from lib.helper import request, send_message, set_new_ci_variable, get_project_info, enable_allowlist, get_allowlist, set_new_allowlist, get_groups_project
from setup.setup_general import set_project_allowlist

logger = logging.getLogger(__name__)

#=======================================================#
#================ Build setup function =================#
#=======================================================#

def get_build_project_variables(token, project):
    """
    Retrieve the existing variables of a project from the GitLab API.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): The project info dictionary.

    Returns:
        project_variables (list): Existing variables retrieved from the GitLab API.
    """
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get('name')
    project_id = project.get("id")

    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
    logger.info(f"Getting variables for {project_name} project")
    project_variables = request("get", url, headers)
    logger.debug(f"project_variables : {project_variables}")

    return project_variables

def create_build_token(headers, project_name, project_id, project_tokens, project_variables):
    """
    Rotate or creates a build token for a GitLab project.

    If a build token owned by the configured GitLab user already exists but a build token variable is not created,
    it is rotated and the variable is created.

    Args:
        headers (dict): The GitLab private token used for authentication.
        project_name (str): The project name.
        project_id (int): The project id.
        project_tokens (list): Existing tokens retrieved from the GitLab API.
        project_variables (list): Existing variables retrieved from the GitLab API.
    """

    build_token_already_created = False
    build_token_id = 0
    build_token_variable_already_created = False
    for token_info in project_tokens :
        if token_info.get("name") == SETUP_BUILD_TOKEN_NAME and not token_info.get("revoked"):
            build_token_already_created = True
            build_token_id = token_info.get("id")
    
    for variable in project_variables :
        if variable.get("key") == SETUP_BUILD_TOKEN_NAME :
            build_token_variable_already_created = True

    token_creation = {}
    in_a_year = date.today() + timedelta(days=365)
    if not build_token_already_created :
        logger.info(f"Build token not created, Creating Build token of {project_name} project")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/access_tokens"
        payload = {
            'name': SETUP_BUILD_TOKEN_NAME,
            'scopes': SETUP_BUILD_TOKEN_SCOPE_DEFAULT,
            'expires_at': in_a_year.strftime("%Y-%m-%d"),
            'access_level': SETUP_BUILD_TOKEN_ACCESS_LEVEL,
        }
        token_creation = request("post", url, headers, payload_json=payload)
    elif build_token_already_created and not build_token_variable_already_created :
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/access_tokens/{build_token_id}/rotate"
        payload = {
            'expires_at': in_a_year.strftime("%Y-%m-%d"),
        }
        token_creation = request("post", url, headers, payload_json=payload)
    
    return token_creation

def config_build_token(token, project, project_variables):
    """
    Configure build token for a GitLab project and setup a corresponding CI variable.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): The project info dictionary.
        project_variables (list): Existing variables retrieved from the GitLab API.
    """

    headers = {"PRIVATE-TOKEN": token}
    build_token = ""
    project_name = project.get('name')
    logger.info(f"Setting Build token of {project_name} project")
    project_id = project.get("id")

    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/access_tokens"
    logger.info(f"Getting tokens of {project_name} project")
    project_tokens = request("get", url, headers)
    logger.debug(f"project_variables : {project_variables}")

    token_creation = create_build_token(headers, project_name, project_id, project_tokens, project_variables)

    if token_creation != {} :
        logger.debug(f"token_creation : {token_creation}")
        build_token = token_creation.get("token")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
        variable_payload = {'key':SETUP_BUILD_TOKEN_NAME, 'value':build_token, 'masked': True}
        set_new_ci_variable(url, headers, project_id, project_variables, variable_payload)


def set_build_ci_variables(token, project, project_variables):
    """
    Setting the build CI variables needed for the build pipeline to work correctly.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): The project info dictionary.
        project_variables (list): Existing variables retrieved from the GitLab API.
    """
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get('name')
    project_id = project.get("id")
    logger.info(f"Setting Build CI variables of {project_name} project")

    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"

    variable_payload = {'key':SETUP_BUILD_ENABLE_BUILD_VARIABLE_NAME, 'value':"yes", 'masked': False}
    variable_already_put = set_new_ci_variable(url, headers, project_id, project_variables, variable_payload)
    if not variable_already_put :
        send_message(SETUP_CHANNEL_URL, f"🔔 Le projet {project_name} a bien été configuré pour utiliser la pipeline de build. Pour plus d'information voir : {SETUP_CI_JOB_URL}")
    
    variable_payload = {'key':SETUP_CICD_CONFIGURATION_PATH_VARIABLE_NAME, 'value':SETUP_CICD_CONFIGURATION_PATH, 'masked': False}
    set_new_ci_variable(url, headers, project_id, project_variables, variable_payload)

    variable_payload = {'key':SETUP_BUILD_DOCKERHUB_TOKEN_VARIABLE_NAME, 'value':SETUP_BUILD_DOCKERHUB_TOKEN, 'masked': True}
    set_new_ci_variable(url, headers, project_id, project_variables, variable_payload)
    variable_payload = {'key':SETUP_BUILD_DEPLOY_TOKEN_VARIABLE_NAME, 'value':SETUP_BUILD_DEPLOY_TOKEN, 'masked': True}
    set_new_ci_variable(url, headers, project_id, project_variables, variable_payload)

def set_build_allowlist(token, project) :
    """
    Adds a project to a GitLab job token allowlist if it is not already included.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): The project info dictionary.
        project_to_allow_name (str): The name of the project to add to the allowlist.
        instance_to_allow_id (int): The ID of the project to add to the allowlist.
    """
    project_name = project.get('name')
    project_instance_to_allow = project.get("instance_to_allow", [])

    project_info = get_project_info(token, project)
    project["namespace_id"] = project_info.get("namespace",{}).get("id")
    for project_to_allow_name, project_to_allow_id in SETUP_BUILD_MANDATORY_ALLOWLIST.items() :
        project_to_allow = {'name': project_to_allow_name, 'id': project_to_allow_id}
        set_project_allowlist(token, project, project_to_allow)

    for instance in project_instance_to_allow :
        instance_type = instance.get('type')
        instance_id = instance.get('id')
        instance_name = instance.get('name')
        logger.info(f"Setting allowlist of {project_name} project and {instance_name} {instance_type} to allow each others")
        set_project_allowlist(token, project, instance)
        if instance_type == 'group' :
            group_projects = get_groups_project(token, instance_id)
            for project_to_setup in group_projects :
                set_project_allowlist(token, project_to_setup, project)