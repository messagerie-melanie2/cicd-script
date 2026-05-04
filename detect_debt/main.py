from lib.gitlab_helper import get_issues, get_registry_info, create_issue, get_issues, update_issue 
from build_docker.find_dockerfiles import find_dockerfiles_r
from detect_debt.global_vars import *

logger = logging.getLogger(__name__)

def main(args) : 
   
    logger.info(f"[General] Scanning {args.path} to find Dockerfiles")

    dockerfiles = find_dockerfiles_r(args.current_repo, args.path)
    
    logger.info(f"Found {len(dockerfiles)} Dockerfiles")
    
    description = ""

    # Creating a dict of all dockerfiles with their versions
    versions = {}
    for x in dockerfiles:
        if x.name not in versions:
            versions[x.name] = []
        versions[x.name].append(x.path.split('/')[-1])

    # Debt analysis   
    for df in dockerfiles:
        # Check only dockerfiles which depend on internal parent
        if not df.parent.external:
            latest = max(versions[df.parent.name])
            if df.parameters.parent_version['version_number'] < latest :
                logger.debug(f"Found technical debt for {df.name} at {df.path}, using parent {df.parent.name} {df.parameters.parent_version['version_number']} but could be using version {latest}")
                description += f"{df.path} using parent {df.parent.name} {df.parameters.parent_version['version_number']} but could be using version {latest}\n"

    # Creating/modifying debt issue
    payload = {'title' : 'Technical debt', 'description' : description, 'labels' : 'En développement', 'assignee_id' : 9401}
    logger.info(f"Payload created : {payload}")

    issue_filter = {'search': 'Technical debt'}

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
