from global_vars import *
from helper import request, send_message, set_new_ci_variable

#=======================================================#
#================ Build setup function =================#
#=======================================================#

def get_build_project_variables(token, project, debug = False):
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get('name')
    project_id = project.get("id")

    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
    print(f"Getting variables for {project_name} project")
    project_variables = request("get", url, headers, debug = debug)
    if debug :
        print(project_variables)

    return project_variables

def config_build_token(token, project, project_variables, debug = False):
    """
    Retrieves or creates a trigger token for a GitLab project.

    If a trigger token owned by the configured GitLab user already exists,
    it is reused. Otherwise, a new trigger token is created.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): The project configuration dictionary.
        debug (bool, optional): Whether to print debug information. Defaults to False.

    Returns:
        None
    """

    headers = {"PRIVATE-TOKEN": token}
    build_token = ""
    project_name = project.get('name')
    print(f"Setting Build token of {project_name} project")
    project_id = project.get("id")

    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/access_tokens"
    print(f"Getting tokens of {project_name} project")
    project_tokens = request("get", url, headers, debug=debug)
    if debug :
        print(project_tokens)

    build_token_already_created = False
    build_token_id = 0
    build_token_variable_already_created = False

    for token_info in project_tokens :
        if token_info.get("name") == SETUP_BUILD_TOKEN_NAME :
            build_token_already_created = True
            build_token_id = token_info.get("id")
    
    for variable in project_variables :
        if variable.get("key") == SETUP_BUILD_TOKEN_NAME :
            build_token_variable_already_created = True

    in_a_year = date.today() + timedelta(days=365)
    if not build_token_already_created :
        print(f"Build token not created, Creating Build token of {project_name} project")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/access_tokens"
        payload = {
            'name': SETUP_BUILD_TOKEN_NAME,
            'scopes': SETUP_BUILD_TOKEN_SCOPE_DEFAULT,
            'expires_at': in_a_year.strftime("%Y-%m-%d"),
            'access_level': SETUP_BUILD_TOKEN_ACCESS_LEVEL,
        }
        response = request("post", url, headers, payload_json=payload, debug=debug)
        if debug :
            print(response)
        build_token = response.get("token")
        set_new_ci_variable(headers, project_id, project_variables, SETUP_BUILD_TOKEN_NAME, build_token, True, debug)
    elif build_token_already_created and not build_token_variable_already_created :
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/access_tokens/{build_token_id}/rotate"
        payload = {
            'expires_at': in_a_year.strftime("%Y-%m-%d"),
        }
        response = request("post", url, headers, payload_json=payload, debug=debug)
        build_token = response.get("token")
        if debug :
            print(build_token)
        set_new_ci_variable(headers, project_id, project_variables, SETUP_BUILD_TOKEN_NAME, build_token, True, debug)


def set_build_ci_variables(token, project, project_variables, debug = False):
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get('name')
    project_id = project.get("id")
    print(f"Setting Build CI variables of {project_name} project")

    set_new_ci_variable(headers, project_id, project_variables, SETUP_BUILD_ENABLE_BUILD_VARIABLE_NAME, "yes", False, debug)
    set_new_ci_variable(headers, project_id, project_variables, SETUP_BUILD_DOCKERHUB_TOKEN_VARIABLE_NAME, SETUP_BUILD_DOCKERHUB_TOKEN, True, debug)

    enable_deploy = project.get("enable_deploy")
    if enable_deploy :
        set_new_ci_variable(headers, project_id, project_variables, SETUP_BUILD_DEPLOY_TOKEN_VARIABLE_NAME, SETUP_BUILD_DEPLOY_TOKEN, True, debug)