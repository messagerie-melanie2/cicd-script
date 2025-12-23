from trigger.global_vars import *
from trigger.trigger_function import read_trigger_parameters_local_file, get_changes, add_local_file_to_config, trigger
logger = logging.getLogger(__name__)

#=======================================================#
#======================== Main =========================#
#=======================================================#

def main(args):
    """
    Main entry point for launching a CI/CD Trigger.

    This function performs the full trigger process:
    1. Delete local proxy to permit request internal url.
    2. Reads trigger configuration variable.
    3. Reads local trigger configuration file if present.
    4. Get changed files of the pipeline launched.
    5. Perform a trigger depending of the project.

    Args:
        args (Namespace): Command-line arguments containing:
            - token (str): Token to use for authentication.
            - project (str): Project that trigger name.
            - branch (str): Actual branch of the pipeline.
            - description (str): Description of the pipeline.
            - commit_before_sha (str): The commit sha of the commit before the actual one.
            - commit_sha (str): The commit sha of the actual commit.
    """

    #Leave proxy
    os.environ["http_proxy"]=""
    os.environ["HTTP_PROXY"]=""
    os.environ["https_proxy"]=""
    os.environ["HTTPS_PROXY"]=""

    trigger_config = env.json(TRIGGER_VARIABLE_CONFIGURATION_KEY_DEFAULT, {})
    trigger_parameters_local_file = read_trigger_parameters_local_file()
    changes = get_changes(args.changes_info_file)

    for project_name,project_config in trigger_config.items() :
        project_config = add_local_file_to_config(project_config, trigger_parameters_local_file)
        trigger(project_name, project_config, args.project, args.branch, args.description, changes, args.token)

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser
parser = argparse.ArgumentParser(
    prog='CICD Python Helper')

parser.add_argument(
    '-tok', '--token', 
    metavar='TOKEN', default=' ',
    help="Token to use for authentication")
parser.add_argument(
    '-p', '--project', 
    metavar='PROJECT_NAME', default=' ',
    help="Project that trigger name")
parser.add_argument(
    '-b', '--branch', 
    metavar='BRANCH', default=' ',
    help="Actual branch of the pipeline")
parser.add_argument(
    '-desc', '--description', 
    metavar='DESCRIPTION', default=' ',
    help="Description of the pipeline")
parser.add_argument(
    '-cif', '--changes-info-file', 
    metavar='FILE', default='changes.txt',
    help="Fichier des changements du commit")

# Run the arguments parser
args = parser.parse_args()

logger.debug(f"args : {args}")

main(args)

# End
print("\r")