# coding=utf-8
from trigger.global_vars import *
from lib.helper import request, add_argument_to_conf
logger = logging.getLogger(__name__)

#=======================================================#
#================== Trigger function ===================#
#=======================================================#

def get_changes(changes_info_file):
    """
    Creating a list of changes by reading a file.

    Args:
        changes_info_file (str): Path of change info file.

    Returns:
        changes (str): Changed files between two commit.
    """
    #Create an array with the files changed during commit
    changes = []
    try:
        # Read changes.txt
        changes_file = open(changes_info_file, 'r')

    except OSError as err:
        logging.debug("changes.txt not found...")
        changes_file = []
    
    for line in changes_file :
        changes.append(line) 
        # changes = ["/debian/3.4/Dockerfile",...]

    return changes

def read_trigger_parameters_local_file():
    """
    Reading local trigger parameters file that can overrides values of project trigger configuration.

    Returns:
        trigger_parameters_local_file (dict): Dictionary loaded from a potential local parameters file.
    """
    trigger_parameters_local_file = {}
    try:
        with open(TRIGGER_PARAMETERS_FILE_NAME, 'r') as trigger_parameters:
            try:
                trigger_parameters_local_file = yaml.safe_load(trigger_parameters)
            except yaml.YAMLError as exc:
                logger.debug(f"{TRIGGER_PARAMETERS_FILE_NAME} file cannot be load...({exc})")
    except Exception as e:
        logger.debug(f"{TRIGGER_PARAMETERS_FILE_NAME} file not found...({e})")
    
    return trigger_parameters_local_file

def add_local_file_to_config(config, trigger_parameters_local_file) :
    """
    Overriding configuration found in local trigger parameters file.

    Args:
        config (dict): Original configuration.
        trigger_parameters_local_file (dict): Configuration found in a local trigger parameters file.

    Returns:
        new_config (dict): New configuration with override values.
    """
    new_config = config.copy()
    for project in trigger_parameters_local_file :
        project_name = project.get('name')
        project_type = project.get('type')
        project_config = new_config.get(project["name"])
        if project_config != None :
            logger.debug(f"{project_name} in trigger_parameters.yml, adding new arguments to config...")
            project_config = project_config | add_argument_to_conf(project, SETUP_TRIGGER_ARGUMENTS, "all")
            project_config = project_config | add_argument_to_conf(project, SETUP_TRIGGER_ARGUMENTS, project_type)
            new_config[str(project_name)] = new_config[str(project_name)] | project_config
        else : 
            logger.debug(f"{project_name} not in trigger_parameters.yml")
    
    return new_config

def check_if_branch_can_trigger(project_name, project_config, branch) :
    """
    Checking if a trigger can be launched depending of branchs_only_trigger parameters and actual branch.

    Args:
        project_name (str): Project to trigger name.
        project_config (dict): Project to trigger configuration.
        branch (str): Actual branch of the pipeline.

    Returns:
        branch_can_trigger (bool): Notice if a trigger can be launched.
    """
    branch_can_trigger = False
    branchs_only_trigger = project_config.get("branchs_only_trigger")

    if branchs_only_trigger == None :
        branch_can_trigger = True
    else :
        if branch in branchs_only_trigger :
            branch_can_trigger = True
    
    if not branch_can_trigger :
        logger.info(f"{branch} branch is not in branchs_only_trigger : {branchs_only_trigger} for project {project_name}, trigger will not be launched")

    return branch_can_trigger

def check_if_file_can_trigger(project_name, project_config, changes_list) :
    """
    Checking if a trigger can be launched depending of trigger_files parameters and files changed of the pipeline launched.

    Args:
        project_name (str): Project to trigger name.
        project_config (dict): Project to trigger configuration.
        changes (list): Changed files of the pipeline launched.

    Returns:
        file_can_trigger (bool): Notice if a trigger can be launched.
    """
    file_can_trigger = False
    trigger_files = project_config.get("trigger_files")

    if trigger_files == None :
        file_can_trigger = True
    else :
        for change in changes_list :
            for file in trigger_files :
                if fnmatch.fnmatch(change,'*' + file + '*') :
                    file_can_trigger = True
    
    if not file_can_trigger :
        logger.info(f"{changes_list} changes is not in trigger_files : {trigger_files} for project {project_name}, trigger will not be launched")

    return file_can_trigger

def get_mapped_branch(initial_branch, project_config) :
    """
    Giving a mapped branch in case branchs_mapping parameters is present.

    Args:
        initial_branch (str): Actual branch of the pipeline.
        project_config (dict): Project to trigger configuration.

    Returns:
        mapped_branch (str): New branch to trigger according to branchs_mapping parameters.
    """
    branchs_mapping = project_config.get("branchs_mapping")

    if branchs_mapping != None :
        for branch, mapping in branchs_mapping.items() :
            if initial_branch == branch :
                mapped_branch = mapping
                logger.info(f"branch {mapped_branch} will be triggered")
            else : 
                logger.debug(f"branch {initial_branch} not in branchs_mapping")
    else : 
        logger.debug("branchs_mapping not in config")
    
    return mapped_branch

def create_payload(project_name, project_config, trigger_project, mapped_branch, initial_branch, description, changes):
    """
    Creating payload needed to request a trigger depending of the project to trigger type.

    Args:
        project_name (str): Project to trigger name.
        project_config (dict): Project to trigger configuration.
        trigger_project (str): Project that trigger name.
        mapped_branch (str): Branch to trigger.
        initial_branch (str): Actual branch of the pipeline.
        description (str): Description of the pipeline.
        changes (list): Changed files of the pipeline launched.

    Returns:
        data (dict): Payload needed to request a trigger depending of the project to trigger type.
    """
    project_type = project_config.get("type")
    trigger_token = os.getenv(project_config.get("token_name"))

    logger.info("Creating payload...")
    data = {}

    if project_type == "gitlab" :
        focus_trigger = project_config.get("focus_trigger")
        variables_json = {}
        for variable in TRIGGER_DESCRIPTION_VARIABLES :
            if variable["tag"] in description :
                variables_json[variable["name"]] = True
        
        data["token"] = trigger_token
        data["ref"] = mapped_branch
        data["variables[CI_PROJECT_TRIGGER]"] = trigger_project
        data["variables[CI_BRANCH_TRIGGER]"] = initial_branch
        data["variables[TRIGGER_DESCRIPTION]"] = description
        data["variables[TRIGGER_VARIABLES]"] = f"{variables_json}"
        if focus_trigger :
            data["variables[CI_CHANGES_TRIGGER]"] = " ".join(changes)
        
    elif project_type == "jenkins" :
        data["pipeline_name"] = project_name
        additional_params = project_config.get("additional_params")
        if additional_params == None :
            logger.debug("additional_params not in config")
        else : 
            data["additional_params"] = additional_params

    logger.info(f"Payload created : {data}")

    return data

def create_url(project_config, mapped_branch, initial_branch) :
    """
    Creating url needed to request a trigger depending of the project to trigger type.

    Args:
        project_config (dict): Project to trigger configuration.
        mapped_branch (str): Branch to trigger.
        initial_branch (str): Actual branch of the pipeline.

    Returns:
        url (str): url needed to request a trigger depending of the project to trigger type.
    """
    project_type = project_config.get("type")
    url = ""

    url_mapping = TRIGGER_URL_MAPPING.get(project_type)
    if url_mapping != None :
        url = url_mapping.get(mapped_branch)
        if url == None :
            logger.warning(f"branch {initial_branch} not in URL_MAPPING of project type {project_type}. Branch {TRIGGER_DEFAULT_BRANCH} will be taken by default")
            url = url_mapping.get(TRIGGER_DEFAULT_BRANCH)
    else :
        logger.debug(f"Project type {project_type} doesn't have url_mapping.")
    
    if project_type == "gitlab" :
        url = GITLAB_URL + 'api/v4/projects/' + str(project_config.get("id"))   + '/trigger/pipeline'
    
    return url

def create_request_auth(project_config, token):
    """
    Creating authentication information needed to request a trigger depending of the project to trigger type.

    Args:
        project_config (dict): Project to trigger configuration.
        token (str): Token to use for authentication.

    Returns:
        request_auth (dict): authentication information needed to request a trigger depending of the project to trigger type.
    """
    project_type = project_config.get("type")
    request_auth = {}
    if project_type == "gitlab" :
        request_auth['auth']=('gitlab-ci-token', token)
    if project_type == "jenkins" :
        trigger_token = os.getenv(project_config.get("token_name"))
        request_auth['headers']= {"token": trigger_token}
    
    return request_auth
    

def trigger(project_name, project_config, trigger_project, branch, description, changes, token):
    if check_if_branch_can_trigger(project_name, project_config, branch) :
        if check_if_file_can_trigger(project_name, project_config, changes) :
            logger.info(f"Launch triggering process of {project_name} project")
            mapped_branch = get_mapped_branch(branch, project_config)
            data = create_payload(project_name, project_config, trigger_project, mapped_branch, branch, description, changes)
            url = create_url(project_config, mapped_branch, branch)
            request_auth = create_request_auth(project_config, token)
            response = request("post",url, headers=request_auth.get("headers"), auth=request_auth.get("auth"), payload_data=data)
            logger.debug(f"Response : {response}")