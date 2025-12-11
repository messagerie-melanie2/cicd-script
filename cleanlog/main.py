# coding=utf-8
from global_vars import *
from cleanlog.cleanlog_function import get_jobs_info, process_jobs

logger = logging.getLogger(__name__)

#=======================================================#
#======================== Main =========================#
#=======================================================#
        
def main(args) :
    """
    Main entry point for deleting log of a project gitlab.

    This function performs the full clean process:
    1. Retrieves the jobs info of the project depending of CLEANLOG_WEEKS_LIMIT parameter.
    2. Process jobs and delete those who exceed CLEANLOG_WEEKS_LIMIT parameter.

    Args:
        args (Namespace): Command-line arguments containing:
            - token (bool): Token to use for authentication.
            - project_id (int): Id of the project.
    """
    jobs = get_jobs_info(args.token,args.project_id,CLEANLOG_WEEKS_LIMIT)
    process_jobs(jobs,args.token,args.project_id,CLEANLOG_WEEKS_LIMIT)

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser and mutually exclusive group
parser = argparse.ArgumentParser(
    prog='CICD Python Helper')
parser.add_argument(
    '-tok', '--token', 
    metavar='TOKEN', default='',
    help="Token to use for authentication")
parser.add_argument(
    '-pid', '--project-id', 
    metavar='PROJECT', default=0,
    help="Id of the project")

# Run the arguments parser
args = parser.parse_args()

logger.debug(f"args : {args}")

main(args)

# End
print("\r")