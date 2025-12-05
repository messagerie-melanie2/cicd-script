from global_vars import *
from setup_general import read_setup_files, set_config_path
from setup_trigger import create_trigger_ci_variables, set_trigger_ci_variables, set_trigger_allowlist
from setup_build import config_build_token, get_build_project_variables, set_build_ci_variables

#=======================================================#
#======================== Main =========================#
#=======================================================#

def main(args) :
    """
    Main entry point for setting up GitLab CI/CD triggers and variables.

    This function performs the full setup process:
    1. Retrieves the GitLab token from environment variables.
    2. Reads setup configuration files from the specified folder.
    3. Sets the CI configuration paths for each project.
    4. Creates and applies CI/CD variables for all projects.
    5. Updates allowlists for projects to enable job token triggers.

    Args:
        args (Namespace): Command-line arguments containing:
            - debug_enabled (bool, optional): Whether to print debug information. Defaults to False.

    Returns:
        None
    """

    token = os.environ.get(SETUP_GITLAB_TOKEN_NAME)
    if (args.setup_trigger):
        all_setup = read_setup_files(SETUP_TRIGGER_FOLDER_PATH, SETUP_TRIGGER_FILE_ENDSWITH, args.debug_enabled)
        for project_to_trigger in all_setup :
            projects_to_setup = project_to_trigger.get("projects")
            set_config_path(token,projects_to_setup, args.debug_enabled)
        all_project_configuration = create_trigger_ci_variables(token,all_setup, args.debug_enabled)
        if args.debug_enabled :
            print(all_project_configuration)
        set_trigger_ci_variables(token, all_project_configuration, args.debug_enabled)
        set_trigger_allowlist(token,all_setup, args.debug_enabled)
    
    if (args.setup_build):
        all_setup = read_setup_files(SETUP_BUILD_FOLDER_PATH, SETUP_BUILD_FILE_ENDSWITH, args.debug_enabled)
        set_config_path(token,all_setup, args.debug_enabled)
        for project_to_setup in all_setup :
            project_to_setup_id = project_to_setup.get("id")
            if project_to_setup_id == 27032:
                project_to_setup_variables = get_build_project_variables(token, project_to_setup, args.debug_enabled)
                config_build_token(token, project_to_setup, project_to_setup_variables, args.debug_enabled)
                set_build_ci_variables(token, project_to_setup, project_to_setup_variables, args.debug_enabled)

            

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser and mutually exclusive group
parser = argparse.ArgumentParser(
    prog='CICD Python Helper',
    description="Program for setting GitLab project")
group = parser.add_mutually_exclusive_group(required=True)
parser.add_argument(
    '-d', '--debug-enabled', 
    metavar='DEBUG', default=False,
    help="Whether to print debug information.")

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

if args.debug_enabled == 'false' :
    args.debug_enabled = False
elif args.debug_enabled == 'true' :
    args.debug_enabled = True

if(args.debug_enabled):
    print(args)

main(args)

# End
print("\r")