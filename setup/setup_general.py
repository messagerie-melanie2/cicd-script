from setup.global_vars import *
from lib.helper import request

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

def set_config_path(token, projects_to_setup):
    """
    Updates the CI configuration path for a list of GitLab projects.

    For each project defined in `projects_to_setup`, this function sends a PUT request
    to update the `ci_config_path` field in the GitLab API. Projects with
    `change_ci` set to False are skipped.

    Args:
        token (str): The GitLab private token used for authentication.
        projects_to_setup (list): A list of project configuration dictionaries loaded
            from setup YAML files.
    """
    files = {
        'ci_config_path': (None, SETUP_GITLAB_CI_CONFIG_PATH),
    }
    headers = {"PRIVATE-TOKEN": token}

    for project in projects_to_setup :
        project_id = project.get("id")
        if project.get("change_ci") != False :
            if project_id == 27188:
                logger.info(f"Setting ci config path of {project.get('name')} project")
                url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
                request("put", url, headers, files=files)