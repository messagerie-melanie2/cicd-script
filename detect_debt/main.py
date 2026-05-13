from detect_debt.global_vars import *
from build_docker.find_dockerfiles import find_dockerfiles_r
from build_docker.create_pipeline import sort_dockerfiles 
from lib.gitlab_helper import get_issues, create_issue, get_issues, update_issue, get_user_id, get_users
from lib.helper import request

logger = logging.getLogger(__name__)

def main(args) : 
   
    logger.info(f"[General] Scanning {args.path} to find Dockerfiles")

    obtained_dockerfiles = find_dockerfiles_r(args.current_repo, args.path)
    
    #internal_debt(obtained_dockerfiles)

    external_debt(obtained_dockerfiles)
    
    # je fais un get sur docker hub pour comparer avec la latest et les niveaux de sécurité

    # je répértorie dans un tableau tout ceux qu'il faut changer et le nombre de dockerfiles enfants impactés
    
    # refacto pour l'issue dette externe
    
    # prometheus et grafana 

    # boolean pour activer ou non la creation ou maj d'issue

def external_debt(dockerfiles):

    sorted_dockerfiles = sort_dockerfiles(dockerfiles)

    logger.debug(f"Dockerfile architecture : \n \
        path : {sorted_dockerfiles[0][0].path} \n \
        name : {sorted_dockerfiles[0][0].name} \n \
        version : {sorted_dockerfiles[0][0].version} \n \
        parent : {sorted_dockerfiles[0][0].parent} \n \
        parent.name : {sorted_dockerfiles[0][0].parent.name} \n \
        parent.version : {sorted_dockerfiles[0][0].parent.version} \n \
        parent.external : {sorted_dockerfiles[0][0].parent.external}")
    
    http_proxy = os.environ.get("HTTP_PROXY")
    https_proxy = os.environ.get("HTTPS_PROXY")
    proxies = {
      "http"  : http_proxy,
      "https" : https_proxy
    }

    description = "| Dockerfile externe | Version actuel | Latest tags |\n|------------|---------------|-----------------|\n"
      
    for df in sorted_dockerfiles[0]:
        # Sanity check if dockerfile is external
        if df.parent.external:
            url = f"https://hub.docker.com/v2/repositories/library/{df.parent.name}/tags?page=1&page_size=100" 
            r = request("get", url, proxies=proxies)
            results = r.get("results")
            latest = next((result for result in results if result.get("name") == "latest"), "no latest tag found")
            if latest != "no latest tag found" :
                latest_digest = latest.get("digest")
                latest_tags = [result.get("name") for result in results if result.get("digest") == latest_digest and result.get("name") != "latest"]
                logger.debug(f"Dockerfile {df.parent.name} {df.parent.version} has latest tags : {latest_tags}")
                if df.parent.version not in latest_tags :
                    description += f"{df.parent.name} | {df.parent.version} | {','.join(latest_tags)}\n"   
            else :
                logger.error(f"No latest tag found  for dockerfile {df.parent.name} {df.parent.version}.")

    # Creating/modifying debt issue
    obtained_users = get_users(args.token, args.project_id)

    obtained_users_id = get_user_id(DETECT_DEBT_ISSUE_ASSIGNEE_USERNAME, obtained_users, False)

    payload = {
        'title' : 'Dette externe',
        'description' : description, 
        'labels' : DETECT_DEBT_ISSUE_LABEL, 
        'assignee_id' : obtained_users_id
    }
    
    issue_filter = {'search': 'Dette externe'}

    create_or_update_issue(payload, issue_filter)

def internal_debt(dockerfiles):

    logger.info(f"Found {len(dockerfiles)} Dockerfiles")
    
    description = "| Dockerfile | Parent actuel | Dernière version |\n|------------|---------------|-----------------|\n"

    # Creating a dict of all dockerfiles with their versions
    versions = {}
    for df in dockerfiles:
        if df.name not in versions:
            versions[df.name] = []
        versions[df.name].append(df.path.split('/')[-1])
    logger.debug(f"Versions found : {versions}")

    # Analysing debt 
    for df in dockerfiles:
        # Check only dockerfiles which depend on internal parent
        if not df.parent.external:
            latest = max(versions[df.parent.name])
            logger.debug(f"{df.name} having parent {df.parent.name} {df.parent.version}")
            if df.parent.version.split('_')[-1] < latest :
                logger.debug(f"Found technical debt for {df.name} at {df.path}, using parent {df.parent.name} {df.parent.version} but could be using version {latest}")
                description += f"{df.path} | {df.parent.name} {df.parent.version} | {latest}\n"

    # Creating/modifying debt issue
    obtained_users = get_users(args.token, args.project_id)

    obtained_users_id = get_user_id(DETECT_DEBT_ISSUE_ASSIGNEE_USERNAME, obtained_users, False)

    payload = {
        'title' : DETECT_DEBT_ISSUE_TITLE,
        'description' : description, 
        'labels' : DETECT_DEBT_ISSUE_LABEL, 
        'assignee_id' : obtained_users_id
    }
    
    issue_filter = {'search': DETECT_DEBT_ISSUE_TITLE}

    create_or_update_issue(payload, issue_filter)

def create_or_update_issue(payload, issue_filter):

    logger.info(f"Payload created : {payload}")

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
