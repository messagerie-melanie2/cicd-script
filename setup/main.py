from setup.global_vars import *
from setup.setup_general import read_setup_files, set_config_path
from setup.setup_trigger import create_trigger_ci_variables, set_trigger_ci_variables, set_trigger_allowlist
from setup.setup_build import config_build_token, get_build_project_variables, set_build_ci_variables

logger = logging.getLogger(__name__)

#=======================================================#
#======================== Main =========================#
#=======================================================#

def main(args) :
    """
    Main entry point for setting up GitLab CI/CD Build or CI/CD Trigger.

    This function performs the full setup process:
    1. Retrieves the GitLab token from environment variables.
    2. Reads setup configuration files from the specified folder.
    3. Sets the CI configuration paths for each project.
    4. Creates and applies CI/CD variables for all projects.
    5. Updates allowlists for projects to enable triggers.

    Args:
        args (Namespace): Command-line arguments containing:
            - setup_trigger (bool, exclusive): Launch a trigger setup.
            - setup_build (bool, exclusive): Launch a build setup.
    """

    token = os.environ.get(SETUP_GITLAB_TOKEN_NAME)
    if (args.setup_trigger):
        all_setup = read_setup_files(SETUP_TRIGGER_FOLDER_PATH, SETUP_TRIGGER_FILE_ENDSWITH)
        for project_to_trigger in all_setup :
            projects_to_setup = project_to_trigger.get("projects")
            set_config_path(token,projects_to_setup)
        all_project_configuration = create_trigger_ci_variables(token,all_setup)
        logger.debug(f"all_project_configuration : {all_project_configuration}")
        set_trigger_ci_variables(token, all_project_configuration)
        set_trigger_allowlist(token,all_setup)
    
    if (args.setup_build):
        all_setup = read_setup_files(SETUP_BUILD_FOLDER_PATH, SETUP_BUILD_FILE_ENDSWITH)
        set_config_path(token,all_setup)
        for project_to_setup in all_setup :
            project_to_setup_id = project_to_setup.get("id")
            if project_to_setup_id == 27188:
                project_to_setup_variables = get_build_project_variables(token, project_to_setup)
                config_build_token(token, project_to_setup, project_to_setup_variables)
                set_build_ci_variables(token, project_to_setup, project_to_setup_variables)

            

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser and mutually exclusive group
parser = argparse.ArgumentParser(
    prog='CICD Python Helper')
group = parser.add_mutually_exclusive_group(required=True)

#####
# Argument to launch setup build
#####
group.add_argument(
    '-sb', '--setup-build', 
    action='store_true',
    help="Setup project to use build feature")

#####
# Argument to launch setup trigger
#####
group.add_argument(
    '-st', '--setup-trigger', 
    action='store_true',
    help="Setup project to use trigger feature")

# Run the arguments parser
args = parser.parse_args()

logger.debug(f"args : {args}")

main(args)

# End
print("\r")