from setup.global_vars import *
from lib.helper import request, send_message, set_new_ci_variable, set_new_allowlist, add_argument_to_conf

logger = logging.getLogger(__name__)

#=======================================================#
#=============== Trigger setup function ================#
#=======================================================#

def config_trigger_token(project, headers, files):
    """
    Retrieves or creates a trigger token for a GitLab project.

    If a trigger token owned by the configured GitLab user already exists,
    it is reused. Otherwise, a new trigger token is created.

    Args:
        project (dict): The project configuration dictionary.
        headers (dict): HTTP headers containing the GitLab authentication token.
        files (dict): Additional form-data fields used when creating a token.

    Returns:
        trigger_token (str): The trigger token for the project (existing or newly created).
    """
    trigger_token = ""
    if project.get("type") == "gitlab" :
        project_name = project.get('name')
        logger.info(f"Setting Trigger token of {project_name} project")
        project_to_trigger_id = project.get("id")

        logger.info(f"Getting Trigger tokens of {project_name} project")
        url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/triggers"
        project_tokens = request("get", url, headers)
        logger.debug(f"project_tokens : {project_tokens}")

        trigger_token_already_created = False

        for token_info in project_tokens :
            if token_info.get("owner").get("username") == SETUP_GITLAB_ACCOUNT_USERNAME :
                trigger_token_already_created = True
                trigger_token = token_info.get("token")
        
        if not trigger_token_already_created :
            logger.info(f"Trigger token not created, Creating Trigger token of {project_name} project")
            response = request("post", url, headers, files=files)
            trigger_token = response.get("token")
            logger.debug(f"trigger_token : {trigger_token}")

    return trigger_token

def create_trigger_project_ci_variable(project, project_to_trigger, trigger_token):
    """
    Builds the CI/CD variable configuration for a project.

    This function merges trigger arguments, identifies the type of target
    project, prepares the appropriate token, and produces
    the final variable payload that will later be written to GitLab.

    Args:
        project (dict): The project receiving CI variables.
        project_to_trigger (dict): The project to be triggered.
        trigger_token (str): The GitLab trigger token (if applicable).
        variable_name (str): The key under which variables should be stored.

    Returns:
        project_configuration (dict): A dictionary containing the full CI variable configuration.
    """
    project_configuration = {}
    variable = {}
    project_name = project.get("name")
    project_to_trigger_type = project_to_trigger.get("type")
    project_to_trigger_name = project_to_trigger.get("name")
    
    project_configuration["name"] = project_name

    variable[project_to_trigger_name] = {}
    variable[project_to_trigger_name] = variable[project_to_trigger_name] | add_argument_to_conf(project, SETUP_TRIGGER_ARGUMENTS, "all")
    variable[project_to_trigger_name] = variable[project_to_trigger_name] | add_argument_to_conf(project, SETUP_TRIGGER_ARGUMENTS, project_to_trigger_type)
    variable[project_to_trigger_name]["type"] = project_to_trigger_type
    
    
    configuration_to_add = {}
    if project_to_trigger_type == "gitlab" :
        project_to_trigger_id = project_to_trigger.get("id")
        configuration_to_add["id"] = project_to_trigger_id
        configuration_to_add["token_name"] = f'{SETUP_GITLAB_VARIABLE_TRIGGER_KEY}_{project_to_trigger_id}'
        configuration_to_add["token"] = trigger_token
    if project_to_trigger_type == "jenkins" :
        token_name = variable[project_to_trigger_name].get("token_name")
        if token_name == None :
            configuration_to_add["token_name"] = SETUP_JENKINS_TRIGGER_TOKEN_NAME
        else :
            configuration_to_add["token_name"] = token_name

        configuration_to_add["token"] = os.environ.get(configuration_to_add.get("token_name"),"")

    variable[project_to_trigger_name] = variable[project_to_trigger_name] | configuration_to_add

    project_configuration = project_configuration | variable

    return project_configuration

def create_trigger_ci_variables(token, all_setup):
    """
    Creates CI/CD variable configurations for all projects defined in setup files.

    This function generates trigger tokens, aggregates variable definitions,
    and prepares a consolidated dictionary grouping all configurations by project ID.

    Args:
        token (str): GitLab private token used for authentication.
        all_setup (list): List of project setup configurations loaded from YAML.

    Returns:
        all_project_configuration (dict): A dictionary mapping each project ID to its CI/CD variable configuration.
    """
    headers = {"PRIVATE-TOKEN": token}
    files_trigger = {
        'description': (None, SETUP_TRIGGER_DESCRIPTION),
    }
    all_project_configuration = {}

    for project_to_trigger in all_setup :
        trigger_token = config_trigger_token(project_to_trigger, headers, files_trigger)
        projects_to_setup = project_to_trigger.get("projects")
        for project in projects_to_setup :
            project_id = project.get("id")
            project_name = project.get("name")

            logger.info(f"Creating project configuration of {project_name} project")
            project_configuration = create_trigger_project_ci_variable(project, project_to_trigger, trigger_token)

            if project_id in all_project_configuration.keys() :
                all_project_configuration[project_id] = all_project_configuration[project_id] | project_configuration
            else :
                all_project_configuration[project_id] = project_configuration

    return all_project_configuration

def set_trigger_ci_variables(token,all_project_configuration):
    """
    Applies all CI/CD variables to GitLab projects based on prepared configuration.

    Retrieves existing variables for each project, updates or creates new ones,
    and sends a notification message when a project is successfully configured
    to trigger another project.

    Args:
        token (str): GitLab private token used for authentication.
        all_project_configuration (dict): Dictionary of all CI variable configurations.

    Returns:
        None
    """
    headers = {"PRIVATE-TOKEN": token}

    for project_id,project_configuration in all_project_configuration.items() :
        if project_id == 27032 :
            project_name = project_configuration.pop('name')

            url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
            logger.info(f"Getting variables for {project_name} project")
            project_variables = request("get", url, headers)
            logger.debug(f"project_variables : {project_variables}")

            for project_to_trigger_name,variable in project_configuration.items() :
                variable_already_put = set_new_ci_variable(headers, project_id, project_variables, variable.get("token_name"), variable.get("token"), True)
                variable.pop("token")
                if not variable_already_put :
                    send_message(SETUP_CHANNEL_URL, f"🔔 Le projet {project_name} a bien été configuré pour trigger le projet {project_to_trigger_name}. Pour plus d'information voir : {SETUP_CI_JOB_URL}")
            
            set_new_ci_variable(headers, project_id, project_variables, TRIGGER_VARIABLE_CONFIGURATION_KEY, json.dumps(project_configuration), False)
            set_new_ci_variable(headers, project_id, project_variables, SETUP_CICD_CONFIGURATION_PATH_VARIABLE_NAME, SETUP_CICD_CONFIGURATION_PATH, False)

def set_trigger_project_allowlist(project, project_to_trigger_name, project_to_trigger_id, project_to_trigger_dependencies, headers):
    """
    Configures GitLab job token allowlists for a project.

    Enables the allowlist, adds the target project and its dependencies,
    and updates group-level allowlists of the target project when necessary.

    Args:
        project (dict): The project whose allowlist is being updated.
        project_to_trigger_name (str): Name of the project that will be triggered.
        project_to_trigger_id (int): ID of the project that will be triggered.
        project_to_trigger_dependencies (list): List of dependency project dictionaries.
        headers (dict): HTTP headers containing the GitLab authentication token.

    Returns:
        None
    """
    project_name = project.get("name")
    project_id = project.get("id")
    logger.info(f"Setting allowlists of {project_name} project")

    if project_id == 27032 :
        logger.info(f"Enabling allowlists of {project_name} project...")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope"
        payload = {'enabled': True}
        request("patch",url, headers, payload_data=payload)
        
        logger.info(f"Getting allowlists of {project_name} project...")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope/allowlist"
        project_allowlist = request("get",url, headers)
        logger.debug(f"project_allowlist : {project_allowlist}")
        
        logger.info(f"Adding to allowlists of {project_name} project, {project_to_trigger_name} project...")
        set_new_allowlist(headers, project_allowlist, project_id, project_to_trigger_id)

        logger.info(f"Adding {project_to_trigger_name} project dependencies to allowlists of {project_name} project...")
        for dependencies in project_to_trigger_dependencies :
            dependencies_id = dependencies.get("id")
            set_new_allowlist(headers, project_allowlist, project_id, dependencies_id)
        
        logger.info(f"Getting allowlists of {project_to_trigger_name} project...")
        url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/job_token_scope/groups_allowlist?per_page=100"
        project_to_trigger_allowlist = request("get", url, headers)
        logger.debug(f"project_to_trigger_allowlist : {project_to_trigger_allowlist}")

        project_to_trigger_allowlist_already_setup = False

        url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
        logger.info(f"Getting {project_name} project info...")
        project_info = request("get", url, headers)
        logger.debug(f"project_info : {project_info}")

        for project in project_to_trigger_allowlist :
            if project.get("id") == project_info.get("namespace",{}).get("id") :
                project_to_trigger_allowlist_already_setup = True
        
        if not project_to_trigger_allowlist_already_setup :
            logger.info(f"Adding {project_name} namespace to allowlists of {project_name} project...")
            url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/job_token_scope/groups_allowlist"
            payload = {'target_group_id': project_info.get("namespace",{}).get("id")}
            request("post",url, headers, payload_data=payload)

def set_trigger_allowlist(token, all_setup):
    """
    Applies allowlist rules for all GitLab projects defined in setup files.

    For each project, this function updates job token scopes, dependencies,
    and group allowlists when applicable.

    Args:
        token (str): GitLab private token for authentication.
        all_setup (list): Project setup configurations loaded from YAML files.

    Returns:
        None
    """
    headers = {"PRIVATE-TOKEN": token}

    for project_to_trigger in all_setup :
        projects_to_setup = project_to_trigger.get("projects")
        project_to_trigger_type = project_to_trigger.get("type")
        project_to_trigger_name = project_to_trigger.get("name")
        project_to_trigger_dependencies = project_to_trigger.get("dependencies", [])
        if project_to_trigger_type == "gitlab" :
            project_to_trigger_id = project_to_trigger.get("id")
            for project in projects_to_setup :
                set_trigger_project_allowlist(project, project_to_trigger_name, project_to_trigger_id, project_to_trigger_dependencies, headers)