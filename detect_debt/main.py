from detect_debt.global_vars import *
from build_docker.find_dockerfiles import find_dockerfiles_r
from detect_debt.detect_debt_function import *

logger = logging.getLogger(__name__)

def main(args) : 
   
    logger.info(f"[General] Scanning {args.path} to find Dockerfiles")

    obtained_dockerfiles = find_dockerfiles_r(args.current_repo, args.path)
    
    internal_debt(args.token, args.project_id, obtained_dockerfiles)

    external_debt(args.token, args.project_id, obtained_dockerfiles)
    
    #TODO je répértorie dans un tableau tout ceux qu'il faut changer et le nombre de dockerfiles enfants impactés
    
    #TODO prometheus et grafana 

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
