from global_vars import *
from helper import request, send_message, set_new_ci_variable

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
        list: Existing variables retrieved from the GitLab API.
    """
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get('name')
    project_id = project.get("id")

    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
    logger.info(f"Getting variables for {project_name} project")
    project_variables = request("get", url, headers)
    logger.debug(f"project_variables : {project_variables}")

    return project_variables

def config_build_token(token, project, project_variables):
    """
    Rotate or creates a build token for a GitLab project.

    If a build token owned by the configured GitLab user already exists but a build token variable is not created,
    it is rotated and the variable is created. Otherwise, a new build token and a new build token variable are created.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): The project info dictionary.
        project_variables (list): Existing variables retrieved from the GitLab API.

    Returns:
        None
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
        response = request("post", url, headers, payload_json=payload)
        logger.debug(f"response : {response}")
        build_token = response.get("token")
        set_new_ci_variable(headers, project_id, project_variables, SETUP_BUILD_TOKEN_NAME, build_token, True)
    elif build_token_already_created and not build_token_variable_already_created :
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/access_tokens/{build_token_id}/rotate"
        payload = {
            'expires_at': in_a_year.strftime("%Y-%m-%d"),
        }
        response = request("post", url, headers, payload_json=payload)
        logger.debug(f"response : {response}")
        build_token = response.get("token")
        set_new_ci_variable(headers, project_id, project_variables, SETUP_BUILD_TOKEN_NAME, build_token, True)


def set_build_ci_variables(token, project, project_variables):
    """
    Setting the build CI variables needed for the build pipeline to work correctly.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): The project info dictionary.
        project_variables (list): Existing variables retrieved from the GitLab API.

    Returns:
        None
    """
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get('name')
    project_id = project.get("id")
    logger.info(f"Setting Build CI variables of {project_name} project")

    variable_already_put = set_new_ci_variable(headers, project_id, project_variables, SETUP_BUILD_ENABLE_BUILD_VARIABLE_NAME, "yes", False)
    set_new_ci_variable(headers, project_id, project_variables, SETUP_CICD_CONFIGURATION_PATH_VARIABLE_NAME, SETUP_CICD_CONFIGURATION_PATH, False)
    if not variable_already_put :
        send_message(SETUP_TRIGGER_CHANNEL_URL, f"🔔 Le projet {project_name} a bien été configuré pour utiliser la pipeline de build. Pour plus d'information voir : {SETUP_CI_JOB_URL}")
    set_new_ci_variable(headers, project_id, project_variables, SETUP_BUILD_DOCKERHUB_TOKEN_VARIABLE_NAME, SETUP_BUILD_DOCKERHUB_TOKEN, True)

    enable_deploy = project.get("enable_deploy")
    if enable_deploy :
        set_new_ci_variable(headers, project_id, project_variables, SETUP_BUILD_DEPLOY_TOKEN_VARIABLE_NAME, SETUP_BUILD_DEPLOY_TOKEN, True)