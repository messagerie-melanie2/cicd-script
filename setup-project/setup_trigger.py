from global_vars import *
from helper import request, send_message

#=======================================================#
#=============== Trigger setup function ================#
#=======================================================#

def read_setup_files(debug = False):
    """
    Reads all trigger setup YAML files and returns a combined list of configurations.

    This function scans the setup directory for all files ending with
    `triggers.yml`, loads their YAML content, and aggregates the result.
    YAML parsing errors can optionally be displayed in debug mode.

    Args:
        debug (bool, optional): Whether to print debug information when a YAML
            file fails to load. Defaults to False.

    Returns:
        list: A list containing all merged YAML configuration entries.
    """
    all_setup = []
    my_path = os.path.abspath(os.path.dirname(__file__))
    my_project_path = my_path.split("cicd-script")[0]
    setup_path = os.path.join(my_project_path, SETUP_TRIGGER_FOLDER_PATH)
    for subdir, dirs, files in os.walk(setup_path):
        for filename in files:
            filepath = subdir + os.sep + filename
            if filepath.endswith("triggers.yml"):
                with open(filepath, 'r') as setup_file:
                    try:
                        setup_yaml = yaml.safe_load(setup_file)
                    except yaml.YAMLError as exc:
                        if debug :
                            print("Couldn't load yaml for {0} file...".format(setup_path))
                            print(exc)
                    else :
                        all_setup = all_setup + setup_yaml
    return all_setup

def set_config_path(token, all_setup, debug = False):
    """
    Updates the CI configuration path for a list of GitLab projects.

    For each project defined in `all_setup`, this function sends a PUT request
    to update the `ci_config_path` field in the GitLab API. Projects with
    `change_ci` set to False are skipped.

    Args:
        token (str): The GitLab private token used for authentication.
        all_setup (list): A list of project configuration dictionaries loaded
            from setup YAML files.
        debug (bool, optional): Whether to print debug information. Defaults to False.

    Returns:
        None
    """
    files = {
        'ci_config_path': (None, SETUP_GITLAB_CI_CONFIG_PATH),
    }
    headers = {"PRIVATE-TOKEN": token}

    for project_to_trigger in all_setup :
        projects_to_setup = project_to_trigger.get("projects")
        for project in projects_to_setup :
            project_id = project.get("id")
            if project.get("change_ci") != False :
                if project_id == 27032 :
                    print(f"Setting ci config path of {project.get('name')} project")
                    url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
                    request("put", url, headers, files=files, debug=debug)

def config_trigger_token(project, headers, files, debug = False):
    """
    Retrieves or creates a trigger token for a GitLab project.

    If a trigger token owned by the configured GitLab user already exists,
    it is reused. Otherwise, a new trigger token is created.

    Args:
        project (dict): The project configuration dictionary.
        headers (dict): HTTP headers containing the GitLab authentication token.
        files (dict): Additional form-data fields used when creating a token.
        debug (bool, optional): Whether to print debug information. Defaults to False.

    Returns:
        str: The trigger token for the project (existing or newly created).
    """
    trigger_token = ""
    if project.get("type") == "gitlab" :
        project_name = project.get('name')
        print(f"Setting Trigger token of {project_name} project")
        project_to_trigger_id = project.get("id")

        print(f"Getting Trigger tokens of {project_name} project")
        url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/triggers"
        project_tokens = request("get", url, headers, debug=debug)
        if debug :
            print(project_tokens)

        trigger_token_already_created = False

        for token_info in project_tokens :
            if token_info.get("owner").get("username") == SETUP_GITLAB_ACCOUNT_USERNAME :
                trigger_token_already_created = True
                trigger_token = token_info.get("token")
        
        if not trigger_token_already_created :
            print(f"Trigger token not created, Creating Trigger token of {project_name} project")
            response = request("post", url, headers, files=files, debug=debug)
            trigger_token = response.get("token")
            if debug :
                print(trigger_token)

    return trigger_token

def add_trigger_argument(project, type) :
    """
    Builds a dictionary of trigger arguments based on global SETUP_TRIGGER_ARGUMENTS settings.

    Args:
        project (dict): The project configuration dictionary.
        type (str): The trigger argument category to extract.

    Returns:
        dict: A dictionary containing the trigger arguments relevant to the given type.
    """
    configuration_to_add = {}
    trigger_argument = SETUP_TRIGGER_ARGUMENTS[type].split(',')

    for argument in trigger_argument :
        value = project.get(argument)
        if value != None :
            configuration_to_add[argument] = value
    
    return configuration_to_add

def create_project_ci_variable(project, project_to_trigger, trigger_token, variable_name):
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
        dict: A dictionary containing the full CI variable configuration.
    """
    project_configuration = {}
    variable = {}
    project_name = project.get("name")
    project_to_trigger_type = project_to_trigger.get("type")
    project_to_trigger_name = project_to_trigger.get("name")
    
    project_configuration["name"] = project_name

    variable[project_to_trigger_name] = {}
    variable[project_to_trigger_name] = variable[project_to_trigger_name] | add_trigger_argument(project,"all")
    variable[project_to_trigger_name] = variable[project_to_trigger_name] | add_trigger_argument(project,project_to_trigger_type)
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

    project_configuration[variable_name] = variable

    return project_configuration

def create_ci_variables(token, all_setup, debug = False):
    """
    Creates CI/CD variable configurations for all projects defined in setup files.

    This function generates trigger tokens, aggregates variable definitions,
    and prepares a consolidated dictionary grouping all configurations by project ID.

    Args:
        token (str): GitLab private token used for authentication.
        all_setup (list): List of project setup configurations loaded from YAML.
        debug (bool, optional): Whether to print debug information. Defaults to False.

    Returns:
        dict: A dictionary mapping each project ID to its CI/CD variable configuration.
    """
    headers = {"PRIVATE-TOKEN": token}
    files_trigger = {
        'description': (None, SETUP_TRIGGER_DESCRIPTION),
    }
    all_project_configuration = {}

    for project_to_trigger in all_setup :
        trigger_token = config_trigger_token(project_to_trigger, headers, files_trigger, debug)
        projects_to_setup = project_to_trigger.get("projects")
        project_to_trigger_type = project_to_trigger.get("type")
        for project in projects_to_setup :
            project_id = project.get("id")
            variable_name = SETUP_VARIABLE_CONFIGURATION_KEY_DEFAULT.get(project_to_trigger_type)
            project_configuration = create_project_ci_variable(project, project_to_trigger, trigger_token, variable_name)

            if project_id in all_project_configuration.keys() :
                if variable_name in all_project_configuration[project_id].keys() :
                    all_project_configuration[project_id][variable_name] = all_project_configuration[project_id][variable_name] | project_configuration[variable_name]
                else :
                    all_project_configuration[project_id][variable_name] = project_configuration[variable_name]
            else :
                all_project_configuration[project_id] = project_configuration

    return all_project_configuration

def set_new_ci_variable(headers, project_id, project_variables, variable_key, variable_value, variable_masked, debug = False) :
    """
    Creates or updates a CI/CD variable for a specific GitLab project.

    If the variable already exists, it is updated. Otherwise, a new variable
    is created.

    Args:
        headers (dict): HTTP headers including the GitLab access token.
        project_id (int): The ID of the project where variables are defined.
        project_variables (list): Existing variables retrieved from the GitLab API.
        variable_key (str): The key/name of the variable.
        variable_value (str): The value to set for the variable.
        variable_masked (bool): Whether the variable should be masked in GitLab.
        debug (bool, optional): Whether to print debug details. Defaults to False.

    Returns:
        bool: True if the variable already existed, False if it was newly created.
    """
    variable_already_put = False

    for variable in project_variables :
        if variable.get("key") == variable_key :
            variable_already_put = True
    
    if variable_already_put :
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables/{variable_key}?value={variable_value}"
        request("put", url, headers, debug = debug)
    else :
        print(f"Setup {variable_key} for {project_id} project")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
        payload = {
            'key': variable_key,
            'value': variable_value,
            'masked': variable_masked,
        }
        request("post", url, headers, payload_data=payload, debug = debug)

    return variable_already_put

def set_ci_variables(token,all_project_configuration, debug = False):
    """
    Applies all CI/CD variables to GitLab projects based on prepared configuration.

    Retrieves existing variables for each project, updates or creates new ones,
    and sends a notification message when a project is successfully configured
    to trigger another project.

    Args:
        token (str): GitLab private token used for authentication.
        all_project_configuration (dict): Dictionary of all CI variable configurations.
        debug (bool, optional): Whether to print debug information. Defaults to False.

    Returns:
        None
    """
    headers = {"PRIVATE-TOKEN": token}

    for project_id,project_configuration in all_project_configuration.items() :
        if project_id == 27032 :
            project_name = project_configuration.pop('name')

            url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
            print(f"Getting variables for {project_name} project")
            project_variables = request("get", url, headers, debug = debug)
            if debug :
                print(project_variables)

            for variable_name in project_configuration.keys() :
                for project_to_trigger_name,variable in project_configuration.get(variable_name).items() :
                    variable_already_put = set_new_ci_variable(headers, project_id, project_variables, variable.get("token_name"), variable.get("token"), True, debug)
                    variable.pop("token")
                    if not variable_already_put :
                        send_message(SETUP_TRIGGER_CHANNEL_URL, f"🔔 Le projet {project_name} a bien été configuré pour trigger le projet {project_to_trigger_name}. Pour plus d'information voir : {SETUP_CI_JOB_URL}")
                
                set_new_ci_variable(headers, project_id, project_variables, variable_name, json.dumps(project_configuration.get(variable_name)), False, debug)


def set_new_allowlist(headers, project_allowlist, project_id, project_to_allow_id, debug = False) :
    """
    Adds a project to a GitLab job token allowlist if it is not already included.

    Args:
        headers (dict): HTTP headers containing the GitLab authentication token.
        project_allowlist (list): List of projects currently in the allowlist.
        project_id (int): The ID of the project whose allowlist is being modified.
        project_to_allow_id (int): The ID of the project to add to the allowlist.
        debug (bool, optional): Whether to print debug information. Defaults to False.

    Returns:
        None
    """
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope/allowlist"
    payload = {'target_project_id': project_to_allow_id}
    project_allowlist_already_setup = False

    for project in project_allowlist :
        if project.get("id") == project_to_allow_id :
            project_allowlist_already_setup = True

    if not project_allowlist_already_setup :
        request("post",url, headers, payload_data=payload, debug=debug)
    else : 
        print("Already added to allowlist.")

def set_project_allowlist(project, project_to_trigger_name, project_to_trigger_id, project_to_trigger_dependencies, headers, debug = False):
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
        debug (bool, optional): Whether to print debug information. Defaults to False.

    Returns:
        None
    """
    project_name = project.get("name")
    project_id = project.get("id")
    print(f"Setting allowlists of {project_name} project")

    if project_id == 27032 :
        print(f"Enabling allowlists of {project_name} project...")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope"
        payload = {'enabled': True}
        request("patch",url, headers, payload_data=payload, debug=debug)
        
        print(f"Getting allowlists of {project_name} project...")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope/allowlist"
        project_allowlist = request("get",url, headers, debug=debug)
        if debug : 
            print(project_allowlist)
        
        print(f"Adding to allowlists of {project_name} project, {project_to_trigger_name} project...")
        set_new_allowlist(headers, project_allowlist, project_id, project_to_trigger_id, debug)

        print(f"Adding {project_to_trigger_name} project dependencies to allowlists of {project_name} project...")
        for dependencies in project_to_trigger_dependencies :
            dependencies_id = dependencies.get("id")
            set_new_allowlist(headers, project_allowlist, project_id, dependencies_id, debug)
        
        print(f"Getting allowlists of {project_to_trigger_name} project...")
        url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/job_token_scope/groups_allowlist?per_page=100"
        project_to_trigger_allowlist = request("get", url, headers, debug=debug)
        if debug : 
            print(project_to_trigger_allowlist)

        project_to_trigger_allowlist_already_setup = False

        url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
        print(f"Getting {project_name} project info...")
        project_info = request("get", url, headers, debug=debug)
        if debug : 
            print(project_info)

        for project in project_to_trigger_allowlist :
            if project.get("id") == project_info.get("namespace",{}).get("id") :
                project_to_trigger_allowlist_already_setup = True
        
        if not project_to_trigger_allowlist_already_setup :
            print(f"Adding {project_name} namespace to allowlists of {project_name} project...")
            url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/job_token_scope/groups_allowlist"
            payload = {'target_group_id': project_info.get("namespace",{}).get("id")}
            request("post",url, headers, payload_data=payload, debug=debug)

def set_allowlist(token, all_setup, debug = False):
    """
    Applies allowlist rules for all GitLab projects defined in setup files.

    For each project, this function updates job token scopes, dependencies,
    and group allowlists when applicable.

    Args:
        token (str): GitLab private token for authentication.
        all_setup (list): Project setup configurations loaded from YAML files.
        debug (bool, optional): Whether to print debug information. Defaults to False.

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
                set_project_allowlist(project, project_to_trigger_name, project_to_trigger_id, project_to_trigger_dependencies, headers, debug)