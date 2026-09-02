from setup.global_vars import *
from lib.helper import request, send_message, add_argument_to_conf
from lib.gitlab_helper import set_new_ci_variable, get_project_info
from setup.setup_general import set_project_allowlist

logger = logging.getLogger(__name__)

#=======================================================#
#=============== Scan setup function ================#
#=======================================================#

def set_sonar_scan_ci_variables(token, project, project_variables):
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

    variable_payload = {'key':SETUP_SONAR_TOKEN_VARIABLE_NAME, 'value':SETUP_SONAR_TOKEN, 'masked': False}
    variable_already_put = set_new_ci_variable(url, headers, project_id, project_variables, variable_payload)
    if not variable_already_put :
        send_message(SETUP_CHANNEL_URL, f"🔔 Le projet {project_name} a bien été configuré pour être scanné par Sonarqube. Pour plus d'information voir : {SETUP_CI_JOB_URL}")