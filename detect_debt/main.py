from lib.gitlab_helper import get_registry_info
from build_docker.find_dockerfiles import find_dockerfiles_r
from detect_debt.global_vars import *

logger = logging.getLogger(__name__)

def main(args) : 
   
    # Optimimser la feature pour ne checker que les nouvelles images / les changements dans les commits ?
    
    logger.info(f"[General] Scanning {args.path} to find Dockerfiles")

    dockerfiles = find_dockerfiles_r(args.current_repo, args.path)
    
    logger.info(f"Found {len(dockerfiles)} Dockerfiles")

    for df in dockerfiles:
        logger.debug(df)

    # Analyse la dette   
    for df in dockerfiles:
        # On check que les dockerfiles dont les parents sont dans notre repo
        if not df.parent.external:
            # On regarde s'il existe une version plus récente du parent
            parents = [x for x in dockerfiles if x.name == df.parent.name]
            latest = max([x.path.split('/')[-1] for x in parents])
            if df.parameters.parent_version['version_number'] < latest :
                logger.info(f"Found technical debt for {df.name} at {df.path}, using parent version {df.parameters.parent_version['version_number']} but could be using version {latest}")

# Créer ou modifie l'issue de la dette technique   

# create_issue

# Prendre exemple sur clean-registry


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

# Run the arguments parser
args = parser.parse_args()

logger.debug(f"args: {args}")

main(args)
