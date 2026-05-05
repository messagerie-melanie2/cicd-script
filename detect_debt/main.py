from detect_debt.global_vars import *
from build_docker.find_dockerfiles import find_dockerfiles_r
from lib.gitlab_helper import get_issues, create_issue, get_issues, update_issue, get_user_id, get_users

logger = logging.getLogger(__name__)

logger.info(logger)

def main(args) : 
   
    logger.info(f"[General] Scanning {args.path} to find Dockerfiles")

    obtained_dockerfiles = find_dockerfiles_r(args.current_repo, args.path)
    
    logger.info(f"Found {len(obtained_dockerfiles)} Dockerfiles")
    
    description = "| Dockerfile | Parent actuel | Dernière version |\n|------------|---------------|-----------------|\n"

    # Creating a dict of all dockerfiles with their versions
    versions = {}
    for df in obtained_dockerfiles:
        if df.name not in versions:
            versions[df.name] = []
        versions[df.name].append(df.path.split('/')[-1])
    logger.debug(f"Versions found : {versions}")

    # Analysing debt 
    for df in obtained_dockerfiles:
        # Check only dockerfiles which depend on internal parent
        if not df.parent.external:
            latest = max(versions[df.parent.name])
            logger.debug(f"{df.name} having parent {df.parent.name} {df.parent.version}")
            logger.debug(f"{df.name} having parent {df.parent.name} {df.parameters.parent_version['version_number']}")
            if df.parent.version < latest :
                logger.debug(f"Found technical debt for {df.name} at {df.path}, using parent {df.parent.name} {df.parent.version} but could be using version {latest}")
                description += f"{df.path} | {df.parent.name} {df.parameters.parent_version['version_number']} | {latest}\n"

    # Creating/modifying debt issue
    obtained_users = get_users(args.token, args.project_id)

    obtained_users_id = get_user_id(DETECT_DEBT_ISSUE_ASSIGNEE_USERNAME, obtained_users, False)

    payload = {
        'title' : DETECT_DEBT_ISSUE_TITLE,
        'description' : description, 
        'labels' : DETECT_DEBT_ISSUE_LABEL, 
        'assignee_id' : obtained_users_id
    }

    logger.info(f"Payload created : {payload}")

    issue_filter = {'search': DETECT_DEBT_ISSUE_TITLE}

    obtained_issues = get_issues(args.token, args.project_id, issue_filter)

    if not obtained_issues:
        create_issue(args.token, args.project_id, payload)
    else:
        update_issue(args.token, args.project_id, obtained_issues[0]["iid"], payload)

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser
parser = argparse.ArgumentParser(
    prog='CICD Python Helper',
    description="Programme permettant de générer une liste de tags (images Docker) à partir d'une arborescence de fichiers (Dockerfile, versions, etc)")

parser.add_argument(
    '-p', '--path', 
    metavar='DIR_PATH', default='.',
    help="Choisir le dossier utilisé comme cible pour la recherche des fichiers (Dockerfiles, versions, etc)")

parser.add_argument(
    '-cr', '--current-repo', 
    metavar='REPO_NAME', default='cicd-docker',
    help="Nom du dépôt git actuel (afin d'identifier les images qui reposent sur un autre dépôt/repo)")

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

logger.debug(f"args: {args}")

main(args)
