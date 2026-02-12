# coding=utf-8
from create_issue.global_vars import *
from lib.gitlab_helper import create_issue_link
from create_issue.create_issue_function import set_and_create_issue

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
    project_user = {}
    meta_issue = []

    if CREATE_ISSUE_META_ISSUE != {} :
        logger.info("Creating meta issue...")
        meta_issue = CREATE_ISSUE_META_ISSUE.copy()
        issues_created,tmp_project_user = set_and_create_issue(args.token, args.project_id, meta_issue, project_user, multiple_user=False)
        meta_issue = issues_created[0]
        project_user = project_user | tmp_project_user
    
    for i in range(1,CREATE_ISSUE_ISSUE_NUMBER + 1) :
        issue_raw = os.environ.get(f"CREATE_ISSUE_ISSUE_{i}")
        issue = json.loads(issue_raw)
        logger.info(f"Creating issue {i} : {issue}...")
        issues_created,tmp_project_user = set_and_create_issue(args.token, args.project_id, issue, project_user, multiple_user=True)
        project_user = project_user | tmp_project_user
        if CREATE_ISSUE_META_ISSUE != {} :
            if meta_issue.get("iid") != None :
                for issue in issues_created : 
                    create_issue_link(args.token, issue, meta_issue)




            

                




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