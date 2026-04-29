from lib.gitlab_helper import get_registry_info
from build_docker.find_dockerfiles import find_dockerfiles_r
from detect_debt.global_vars import *

logger = logging.getLogger(__name__)

def main(args) : 

    # Récupérer les infos des paths dans un projet  *-docker  
    registry = get_registry_info(args.token, args.project_id) # pas besoin du registry pour le script mais on prends les infos quand même
    logger.debug(f"Contenu registry, args.token : {args.token} et args.project_id {args.project_id}") 
    
    # Optimimser la feature pour ne checker que les nouvelles images / les changements dans les commits ?
    
    logger.info(f"[General] Scanning {args.path} to find Dockerfiles")

    dockerfiles = find_dockerfiles_r(args.current_repo, args.path)
    
    logger.info(f"Found {len(dockerfiles)} Dockerfiles")

    for df in dockerfiles:
        logger.debug(df)

# Analyse la dette   

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
    '-tok', '--token', 
    metavar='TOKEN_STRING', default='',
    help="Token to get registry")

parser.add_argument(
    '-pid', '--project-id', 
    metavar='ID', default='',
    help="L'id du projet pour récupéré sa registry")

parser.add_argument(
    '-cr', '--current-repo', 
    metavar='REPO_NAME', default='cicd-docker',
    help="Nom du dépôt git actuel (afin d'identifier les images qui reposent sur un autre dépôt/repo)")

# Run the arguments parser
args = parser.parse_args()

logger.debug(f"args: {args}")

main(args)
