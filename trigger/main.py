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

    Returns:
        None
    """

    #Leave proxy
    os.environ["http_proxy"]=""
    os.environ["HTTP_PROXY"]=""
    os.environ["https_proxy"]=""
    os.environ["HTTPS_PROXY"]=""

    trigger_config = env.json(TRIGGER_VARIABLE_CONFIGURATION_KEY_DEFAULT, {})
    trigger_parameters_local_file = read_trigger_parameters_local_file()
    changes = get_changes(args.commit_before_sha,args.commit_sha)

    for project_name,project_config in trigger_config.items() :
        project_config = add_local_file_to_config(project_config, trigger_parameters_local_file)
        trigger(project_name, project_config, args.project, args.branch, args.description, changes, args.token)

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser
parser = argparse.ArgumentParser(
    prog='CICD Python Helper',
    description="Programme permettant de gérer les logs/artifacts des projets gitlab")

parser.add_argument(
    '-tok', '--token', 
    metavar='TOKEN', default=' ',
    help="Token pour accéder à gitlab")
parser.add_argument(
    '-p', '--project', 
    metavar='PROJECT_NAME', default=' ',
    help="Nom du projet qui trigger")
parser.add_argument(
    '-b', '--branch', 
    metavar='BRANCH', default=' ',
    help="Branche qui trigger")
parser.add_argument(
    '-desc', '--description', 
    metavar='DESCRIPTION', default=' ',
    help="Decription du trigger")
parser.add_argument(
    '-cbs', '--commit-before-sha', 
    metavar='COMMIT_BEFORE_SHA', default=' ',
    help="Sha du commit précedent")
parser.add_argument(
    '-cs', '--commit-sha', 
    metavar='COMMIT_SHA', default=' ',
    help="Sha du commit actuelle")

# Run the arguments parser
args = parser.parse_args()

main(args)

# End
print("\r")