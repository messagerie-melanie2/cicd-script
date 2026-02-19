from setup.global_vars import *
from lib.gitlab_helper import request, set_new_ci_variable, enable_allowlist, get_allowlist, set_new_allowlist

logger = logging.getLogger(__name__)

def read_setup_files(folder_path, file_endswith):
    """
    Reads all file setup YAML files and returns a combined list of configurations.

    This function scans the setup directory for all files ending with
    file_endwith , loads their YAML content, and aggregates the result.
    YAML parsing errors can optionally be displayed in debug mode.

    Args:
        folder_path (str): The folder path where all YAML setup file are located.
        file_endswith (str): The string that decide what is a setup file.

    Returns:
        all_setup (list): A list containing all merged YAML configuration entries.
    """
    all_setup = []
    my_path = os.path.abspath(os.path.dirname(__file__))
    my_project_path = my_path.split("cicd-script")[0]
    setup_path = os.path.join(my_project_path, folder_path)
    for subdir, dirs, files in os.walk(setup_path):
        for filename in files:
            filepath = subdir + os.sep + filename
            if filepath.endswith(file_endswith):
                with open(filepath, 'r') as setup_file:
                    try:
                        setup_yaml = yaml.safe_load(setup_file)
                    except yaml.YAMLError as exc:
                        logger.debug(f"Couldn't load yaml for {setup_path} file...")
                        logger.debug(exc)
                    else :
                        all_setup = all_setup + setup_yaml
    return all_setup

def set_config_path(token, project):
    """
    Updates the CI configuration path for a list of GitLab projects.

    For each project defined in `projects_to_setup`, this function sends a PUT request
    to update the `ci_config_path` field in the GitLab API. Projects with
    `change_ci` set to False are skipped.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): Project configuration loaded from setup YAML files.
    """
    files = {
        'ci_config_path': (None, SETUP_GITLAB_CI_CONFIG_PATH),
    }
    headers = {"PRIVATE-TOKEN": token}
    project_id = project.get("id")
    if project.get("change_ci") != False :
        logger.info(f"Setting ci config path of {project.get('name')} project")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
        request("put", url, headers, files=files)

def set_schedule(token, project_id, schedule_to_set):
    """
    Setting schedules and schedules variables of a project.

    Args:
        token (str): The GitLab private token used for authentication.
        project_id (id): Project id to setup schedule.
        schedules_to_set (dict): A dict containing all schedule to set with their values for the project.
    """
    headers = {"PRIVATE-TOKEN": token}
    schedule_already_setup = False
    schedule_created = {}
    schedule_to_set_description = schedule_to_set.get("description")
    schedule_to_set_cron = schedule_to_set.get("cron")
    schedule_to_set_cron_timezone = schedule_to_set.get("cron_timezone")
    schedule_to_set_variables = schedule_to_set.get("variables")
    schedule_to_set_branch = schedule_to_set.get("branch")

    logger.info(f"Creating {schedule_to_set_description} schedule...")

    logger.info(f"Getting project schedules...")
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/pipeline_schedules"
    project_schedules = request("get", url, headers)

    for schedule in project_schedules :
        owner = schedule.get("owner")
        if schedule_to_set_description in schedule.get("description") :
            schedule_already_setup = True
            schedule_created = schedule
        if owner is not None :
            if owner.get("username") != SETUP_GITLAB_ACCOUNT_USERNAME :
                logger.info(f"Taking ownership of {schedule.get('description')} schedule...")
                url = f"{GITLAB_URL}/api/v4/projects/{project_id}/pipeline_schedules/{schedule.get('id')}/take_ownership"
                request("post", url, headers)
    
    files = {
            'description': (None, schedule_to_set_description),
            'ref': (None, schedule_to_set_branch),
            'cron': (None, schedule_to_set_cron),
            'cron_timezone': (None, schedule_to_set_cron_timezone),
            'active': (None, 'true'),
        }
    
    if not schedule_already_setup :
        logger.info(f"Schedule not created. Creating...")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/pipeline_schedules"
        schedule_created = request("post", url, headers, files=files)
    else :
        logger.info(f"Schedule already created. Modifying...")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/pipeline_schedules/{schedule_created.get('id')}"
        schedule_created = request("put", url, headers, files=files)

    for key,value in schedule_to_set_variables.items() :
        schedule_variable_info = []
        variable_payload = {"key": key, "value": value }

        #FOR GITLAB IN 18.7
        #logger.info(f"Getting {key} variable...")
        #url = f"{GITLAB_URL}/api/v4/projects/{project_id}/pipeline_schedules/{schedule_created.get('id')}/variables/{key}"
        #schedule_variable_info.append(request("get", url, headers))

        #FOR GITLAB < 18.7
        if schedule_already_setup :
            schedule_variable_info.append(variable_payload)
        
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/pipeline_schedules/{schedule_created.get('id')}/variables"
        set_new_ci_variable(url, headers, project_id, schedule_variable_info, variable_payload)


def config_schedule(token, project, schedules_to_set_default):
    """
    Creation of a dictionnary of all schedule to setup for a project based on default schedule and modified by values on yaml configuration files.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): Project configuration dictionaries loaded from setup YAML files.
        schedules_to_set_default (dict): Default value of schedule based on schedule type.
    
    Returns:
        schedules_to_set (dict): A dict containing all schedule to set with their values for the project.
    """
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get('name')
    project_id = project.get("id")
    project_schedules = project.get("schedule",[])
    schedules_to_set = {}

    logger.info(f"Getting {project_name} default branch.")
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
    project_info = request("get", url, headers)
    project_default_branch = f"refs/heads/{project_info.get('default_branch')}"

    logger.info(f"Setting {project_name} schedules.")

    logger.debug("Setting mandatory schedule...")
    for mandatory_schedule in SETUP_SCHEDULE_MANDATORY :
        mandatory_schedule_branch = schedules_to_set_default[mandatory_schedule].get("branch")
        if mandatory_schedule_branch == None :
            mandatory_schedule_branch = project_default_branch
        schedule_key = f"{mandatory_schedule}-{mandatory_schedule_branch}"
        schedules_to_set[schedule_key] = copy.deepcopy(schedules_to_set_default[mandatory_schedule])
        schedules_to_set[schedule_key]["description"] = f"[{mandatory_schedule_branch}] {schedules_to_set[schedule_key]['description']}"
        schedules_to_set[schedule_key]["branch"] = mandatory_schedule_branch
    logger.debug(f"Mandatory default schedule : {schedules_to_set}")
    
    for schedule in project_schedules :
        schedule_type = schedule.pop("type")
        schedule_branch = schedule.get("branch")
        if schedule_branch == None :
            schedule_branch = project_default_branch
        schedule["branch"] = schedule_branch
        schedule_key = f"{schedule_type}-{schedule_branch}"
        logger.debug(f"schedule_key: {schedule_key}")
        schedules_to_set[schedule_key] = copy.deepcopy(schedules_to_set_default.get(schedule_type,SETUP_BUILD_DEFAULT_SCHEDULE))
        
        for key,value in schedule.items() :
            logger.debug(f"Schedule to set before: {schedules_to_set}")
            logger.debug(f"key: {key}, value : {value}")
            if key != "variables" :
                schedules_to_set[schedule_key][key] = value
            else :
                for variable_key,variable_value in value.items() :
                    schedules_to_set[schedule_key][key][variable_key] = variable_value
            
            logger.debug(f"Schedule to set after: {schedules_to_set}")

        schedules_to_set[schedule_key]["description"] = f"[{schedule_branch}] {schedules_to_set[schedule_key]['description']}"

    return schedules_to_set


def set_project_allowlist(token, project, instance_to_allow):
    """
    Configures GitLab job token allowlists for a project.

    Enables the allowlist, adds the target project and its dependencies,
    and updates group-level allowlists of the target project when necessary.

    Args:
        token (str): The GitLab private token used for authentication.
        project (dict): The project whose allowlist is being updated.
        instance_to_allow (dict): The project that need to be allowed.
    """
    headers = {"PRIVATE-TOKEN": token}
    project_name = project.get("name")
    project_id = project.get("id")
    instance_to_allow_name = instance_to_allow.get("name")
    instance_to_allow_type = instance_to_allow.get("instance_type",'project')
    instance_to_allow_id = instance_to_allow.get("id")
    instance_to_allow_dependencies = instance_to_allow.get("dependencies", [])

    suffix = "allowlist?per_page=100"
    if instance_to_allow_type == 'group' :
        suffix = f"groups_{suffix}"
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope/{suffix}"

    enable_allowlist(token, project)
    
    project_allowlist = get_allowlist(token, project, instance_to_allow_type)
    
    logger.info(f"Adding {instance_to_allow_name} {instance_to_allow_type} to allowlists of {project_name} project...")
    payload_arg = f"target_{instance_to_allow_type}_id"
    payload = {payload_arg: instance_to_allow_id}
    set_new_allowlist(url, headers, project_allowlist, payload, instance_to_allow_id)

    logger.info(f"Adding {instance_to_allow_name} {instance_to_allow_type} dependencies to allowlists of {project_name} project...")
    for dependencies in instance_to_allow_dependencies :
        dependencies_id = dependencies.get("id")
        dependencies_name = dependencies.get("name")
        dependencies_type = dependencies.get("instance_type")
        logger.info(f"Adding {dependencies_name} {dependencies_type} to allowlists of {project_name} project...")
        payload_arg = f"target_{dependencies_type}_id"
        payload = {payload_arg: dependencies_id}
        set_new_allowlist(url, headers, project_allowlist, payload, dependencies_id)