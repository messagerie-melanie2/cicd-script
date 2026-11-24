from setup.global_vars import *
from lib.helper import request, send_message, add_argument_to_conf
from lib.gitlab_helper import set_new_ci_variable, get_project_info
from setup.setup_general import set_project_allowlist

logger = logging.getLogger(__name__)

#=======================================================#
#============== Sonarqube setup function ===============#
#=======================================================#

def set_sonar_scan_ci_variables(token, project, project_variables):
    """
    Setting the CI variables needed for the Sonarqube scan to work correctly.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): The project info dictionary.
        project_variables (list): Existing variables retrieved from the GitLab API.
    """
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get('name')
    project_id = project.get("id")
    logger.info(f"Setting Scan CI variables of {project_name} project")

    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"

    variable_payload = {'key':SETUP_SONAR_PROJECT_TOKEN_VARIABLE_NAME, 'value':SETUP_SONAR_TOKEN, 'masked': False}
    variable_already_put = set_new_ci_variable(url, headers, project_id, project_variables, variable_payload)
    if not variable_already_put :
        send_message(SETUP_CHANNEL_URL, f"🔔 Le projet {project_name} a bien été configuré pour être scanné par Sonarqube. Pour plus d'information voir : {SETUP_CI_JOB_URL}")

def set_sonar_main_branch(sonar_auth, project_key, main_branch):
    """
    Rename the main branch of a Sonarqube project so it matches the GitLab default branch.

    Args:
        project_key (str): The Sonarqube project key.
        main_branch (str): The GitLab default branch of the project.
    """

    url = f"{SETUP_SONAR_HOST_URL}/api/project_branches/list"
    project_branches = request("get", url, auth=sonar_auth, params={"project": project_key}).get("branches", [])
    logger.debug(f"project_branches : {project_branches}")

    sonar_main_branch = None
    for branch in project_branches :
        if branch.get("isMain") :
            sonar_main_branch = branch.get("name")

    if sonar_main_branch == main_branch :
        logger.info(f"Main branch of {project_key} Sonarqube project is already {main_branch}.")
    else :
        logger.info(f"Renaming main branch of {project_key} Sonarqube project from {sonar_main_branch} to {main_branch}...")
        url = f"{SETUP_SONAR_HOST_URL}/api/project_branches/rename"
        request("post", url, auth=sonar_auth, payload_data={"project": project_key, "name": main_branch})

def get_sonar_alm_setting(sonar_auth, project_key):
    """
    Get the key of the GitLab DevOps Platform Integration to use for a Sonarqube project.

    SETUP_SONAR_ALM_SETTING is used if not empty.
    Otherwise, it is auto-detected if exactly one GitLab integration is available for the project
    (api/alm_settings/list with the project parameter only needs the 'Administer' permission on the project).

    Args:
        project_key (str): The Sonarqube project key.

    Returns:
        alm_setting (str): The GitLab integration key, or None if it can't be found.
    """
    if SETUP_SONAR_ALM_SETTING != "" :
        return SETUP_SONAR_ALM_SETTING

    url = f"{SETUP_SONAR_HOST_URL}/api/alm_settings/list"
    alm_settings = request("get", url, auth=sonar_auth, params={"project": project_key}).get("almSettings", [])
    logger.debug(f"alm_settings : {alm_settings}")

    gitlab_settings = [alm_setting for alm_setting in alm_settings if alm_setting.get("alm") == "gitlab"]
    if len(gitlab_settings) != 1 :
        logger.error(f"{len(gitlab_settings)} GitLab integration(s) available for {project_key} Sonarqube project, can't choose one. Set SETUP_SONAR_ALM_SETTING.")
        return None

    return gitlab_settings[0].get("key")

def set_sonar_gitlab_binding(sonar_auth, project_key, gitlab_project_id):
    """
    Bind a Sonarqube project to its GitLab repository (DevOps Platform Integration).

    The binding is always set: set_gitlab_binding creates it, or replaces it if it already exists.
    (Reading it first with get_binding is avoided: Sonarqube answers 404 when the project is not bound yet.)

    Args:
        sonar_auth (tuple): The Sonarqube API token authentication.
        project_key (str): The Sonarqube project key.
        gitlab_project_id (int): The GitLab project id.
    """
    alm_setting = get_sonar_alm_setting(sonar_auth, project_key)
    if alm_setting is None :
        logger.error(f"Skipping GitLab binding of {project_key} Sonarqube project.")
        return

    logger.info(f"Binding {project_key} Sonarqube project to GitLab project {gitlab_project_id} with {alm_setting} integration...")
    url = f"{SETUP_SONAR_HOST_URL}/api/alm_settings/set_gitlab_binding"
    payload = {
        "almSetting": alm_setting,
        "project": project_key,
        "repository": gitlab_project_id,
        "monorepo": "false",
    }
    request("post", url, auth=sonar_auth, payload_data=payload)

def set_sonar_project(token, project):
    """
    Create the project on Sonarqube (if it doesn't exist), align its main branch with the GitLab default branch
    and bind it to its GitLab repository.

    The Sonarqube instance is the one of SONAR_HOST_URL, authenticated with the token of SETUP_SONAR_API_TOKEN_VARIABLE_NAME.
    The Sonarqube project key is the GitLab project path with "/" replaced by ":" (same rule as before_scan.sh),
    unless the optional "sonar_project_key" field is set on the project.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): The project info dictionary.
    """
    project_name = project.get('name')

    if SETUP_SONAR_HOST_URL == "" or SETUP_SONAR_API_TOKEN == "" :
        logger.error(f"SONAR_HOST_URL or {SETUP_SONAR_API_TOKEN_VARIABLE_NAME} variable is empty, can't configure {project_name} project on Sonarqube.")
        return

    project_info = get_project_info(token, project)
    project_path = project_info.get("path_with_namespace")
    main_branch = project_info.get("default_branch")
    if project_path is None or main_branch is None :
        logger.error(f"Couldn't get path or default branch of {project_name} project, skipping Sonarqube configuration.")
        return

    project_key = project.get("sonar_project_key", project_path.replace("/", ":"))
    sonar_auth = (SETUP_SONAR_API_TOKEN, "")

    # api/components/show only needs the 'Browse' permission on the project
    # (api/projects/search would need the 'Administer System' permission). A 404 means the project doesn't exist.
    logger.info(f"Searching {project_key} project on Sonarqube ({SETUP_SONAR_HOST_URL})...")
    url = f"{SETUP_SONAR_HOST_URL}/api/components/show"
    sonar_project = request("get", url, auth=sonar_auth, params={"component": project_key}, ignored_status_codes=[404])

    if sonar_project != {} :
        logger.info(f"{project_key} project already exists on Sonarqube.")
    else :
        logger.info(f"{project_key} project not created on Sonarqube. Creating...")
        url = f"{SETUP_SONAR_HOST_URL}/api/projects/create"
        payload = {
            "project": project_key,
            "name": project_name,
            "mainBranch": main_branch,
        }
        project_created = request("post", url, auth=sonar_auth, payload_data=payload)
        if project_created == {} :
            logger.error(f"Couldn't create {project_key} project on Sonarqube.")
            return

    set_sonar_main_branch(sonar_auth, project_key, main_branch)
    set_sonar_gitlab_binding(sonar_auth, project_key, project.get("id"))
