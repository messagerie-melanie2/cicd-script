from global_vars import *
from setup_trigger import read_setup_files, set_config_path, create_ci_variables, set_ci_variables, set_project_allowlist

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
    all_setup = read_setup_files(debug = args.debug_enabled)
    set_config_path(token,all_setup, debug = args.debug_enabled)
    all_project_configuration = create_ci_variables(token,all_setup, debug = args.debug_enabled)
    if args.debug_enabled :
        print(all_project_configuration)
    set_ci_variables(token, all_project_configuration, debug = args.debug_enabled)
    set_project_allowlist(token,all_setup, debug = args.debug_enabled)

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser and mutually exclusive group
parser = argparse.ArgumentParser(
    prog='CICD Python Helper',
    description="Program for setting GitLab project")
parser.add_argument(
    '-d', '--debug-enabled', 
    metavar='DEBUG', default=False,
    help="Whether to print debug information.")

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