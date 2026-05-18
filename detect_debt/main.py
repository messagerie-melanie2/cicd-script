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
    
    # je répértorie dans un tableau tout ceux qu'il faut changer et le nombre de dockerfiles enfants impactés
    
    # prometheus et grafana 

    # boolean pour activer ou non la creation ou maj d'issue

    # boolean pour activer ou non dirty comparaison

    # CONSTANTES différenciées pour interne / externe à update dans les fichiers conf : anto-docker, mel-docker, configuration/defaultconf.yml

    # L'idée c'est de faire une requête sur la version actuelle, récupérer tous les tags qui correspondent à son sha256 et récupérer la version la plus précise possible (genre 1.29.8-alpine, garder 1.29.8 au lieu de "alpine")
    # Comparer avec la version la plus précise possible obtenue par les tags du latest
    # Si on a la même version, ça veut dire que c'est une image alternative qui a un sha256 différent parce qu'une image modifiée mais qui possède la même version de la technologie donc c'est bon.

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
    
    logger.info(f"{len(sorted_dockerfiles[0])} external dockerfiles found.")

    http_proxy = os.environ.get("HTTP_PROXY")
    https_proxy = os.environ.get("HTTPS_PROXY")
    proxies = {
      "http"  : http_proxy,
      "https" : https_proxy
    }

    description = "| Dockerfile | Version actuel | Latest tags |\n|------------|---------------|-----------------|\n"
      
    for df in sorted_dockerfiles[0]:

        if df.parent.external: # Sanity check, dockerfiles should be external in the first array
        
            # Getting tags from dockerhub
            url = f"https://hub.docker.com/v2/repositories/library/{df.parent.name}/tags?page=1&page_size=1000" 
            r = request("get", url, proxies=proxies)
            results = r.get("results")

            # Getting "latest" tag and current tag elements
            latest = [result for result in results if result.get("name") == "latest"]
            current = [result for result in results if result.get("name") == df.parent.version] 

            if latest: # Sanity check latest is not empty
                if current: # Sanity check current is not empty

                    # Getting all the tags corresponding to latest 
                    latest_digest = latest[0].get("digest")
                    latest_tags = [result.get("name") for result in results if result.get("digest") == latest_digest and result.get("name") != "latest"]

                    # Getting all the tags corresponfing to current version
                    current_digest = current[0].get("digest") 
                    current_tags = [result.get("name") for result in results if result.get("digest") == current_digest]

                    logger.debug(f"Dockerfile {df.parent.name} {df.parent.version} has latest tags : {latest_tags} and current tags : {current_tags}")
                    
                    # Filling the description with latest_tags
                    if df.parent.version not in latest_tags :
                        description += f"{df.path} | {df.parent.version} | {', '.join(latest_tags)}\n"   

                else :
                    logger.error(f"No current tag found  for dockerfile {df.parent.name} {df.parent.version}.")
            else :
                logger.error(f"No latest tag found  for dockerfile {df.parent.name} {df.parent.version}.")

    logger.info(f"=== External debt found === \n {description}")

    # Creating/modifying debt issue
    obtained_users = get_users(args.token, args.project_id)

    obtained_users_id = get_user_id(DETECT_EXTERNAL_DEBT_ISSUE_ASSIGNEE_USERNAME, obtained_users, False)

    payload = {
        'title' : DETECT_EXTERNAL_DEBT_ISSUE_TITLE,
        'description' : description, 
        'labels' : DETECT_EXTERNAL_DEBT_ISSUE_LABEL, 
        'assignee_id' : obtained_users_id
    }
    
    issue_filter = {'search': DETECT_EXTERNAL_DEBT_ISSUE_TITLE}

    if DETECT_EXTERNAL_DEBT_ACTIVATE : create_or_update_issue(payload, issue_filter)

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

    logger.info(f"=== Internal debt found === \n {description}")

    # Creating/modifying debt issue
    obtained_users = get_users(args.token, args.project_id)

    obtained_users_id = get_user_id(DETECT_INTERNAL_DEBT_ISSUE_ASSIGNEE_USERNAME, obtained_users, False)

    payload = {
        'title' : DETECT_INTERNAL_DEBT_ISSUE_TITLE,
        'description' : description, 
        'labels' : DETECT_INTERNAL_DEBT_ISSUE_LABEL, 
        'assignee_id' : obtained_users_id
    }
    
    issue_filter = {'search': DETECT_INTERNAL_DEBT_ISSUE_TITLE}

    if DETECT_INTERNAL_DEBT_ACTIVATE : create_or_update_issue(payload, issue_filter)

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
