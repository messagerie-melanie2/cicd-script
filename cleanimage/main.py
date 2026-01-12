# coding=utf-8
from global_vars import *
from lib.gitlab_helper import get_registry_info
from lib.helper import get_changes
from dockerbuild.find_dockerfiles import find_dockerfiles_r
from cleanimage.clean_no_build import clean_ghost_images
from cleanimage.clean_dev import clean_dev_images

logger = logging.getLogger(__name__)

def main(args) :
    #Find the registry of the project 
    registry = get_registry_info(args.token, args.project_id)

    #Create an array with the files changed during commit
    changes = get_changes(args.changes_info_file)

    # Find all Dockerfiles in the current path
    logger.info(f"[General] Scanning {args.path} to find Dockerfiles")
    dockerfiles_to_build = find_dockerfiles_r(args.generate_jsonnet_current_repo, args.path, args.generate_jsonnet_branch_name if(args.generate_jsonnet) else NO_BRANCH, changes, registry, args.trigger_project, args.trigger_changes)
    logger.info(f'Found {len(dockerfiles_to_build)} docker images to build.')

    #####
    # Finding tags of 'NO_BUILD' Docker images
    #####
    if(args.delete_ghost_image):
        clean_ghost_images(registry,dockerfiles_to_build,args.token, args.project_id)

    if(args.delete_dev_image):
        clean_dev_images(registry,args.token, args.project_id)


#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser and mutually exclusive group
parser = argparse.ArgumentParser(
    prog='CICD Python Helper',
    description="Programme permettant de générer une liste de tags (images Docker) à partir d'une arborescence de fichiers (Dockerfile, versions, etc)")
group = parser.add_mutually_exclusive_group(required=True)
parser.add_argument(
    '-p', '--path', 
    metavar='DIR_PATH', default='.',
    help="Choisir le dossier utilisé comme cible pour la recherche des fichiers (Dockerfiles, versions, etc)")

#####
# Argument to process Dockerfiles
#####
parser.add_argument(
    '-cr', '--current-repo', 
    metavar='REPO_NAME', default='cicd-docker',
    help="Nom du dépôt git actuel (afin d'identifier les images qui reposent sur un autre dépôt/repo)")
parser.add_argument(
    '-bn', '--branch-name', 
    metavar='BRANCH_NAME', default=NO_BRANCH,
    help="Nom de la branche git actuelle, à intégrer dans le tag des images Docker")
parser.add_argument(
    '-pf', '--pipeline-folder', 
    metavar='FILE_PATH', default="/cicd-docker/pipelines",
    help="Nom de la branche git actuelle, à intégrer dans le tag des images Docker")

#####
# Argument to find if parents needs to be build
#####
parser.add_argument(
    '-cif', '--changes-info-file', 
    metavar='FILE', default='changes.txt',
    help="Fichier des changements du commit")
    
parser.add_argument(
    '-tok', '--token', 
    metavar='TOKEN_STRING', default='',
    help="Token to get registry")
parser.add_argument(
    '-pid', '--project-id', 
    metavar='ID', default='',
    help="L'id du projet pour récupéré sa registry")

#####
# Argument to delete dev image
#####
group.add_argument(
    '-ddi', '--delete-dev-image',
    action='store_true',
    help="Lance la suppression de toutes les images de dev non utilisé")

#####
# Argument to delete ghost image
#####
group.add_argument(
    '-dgi', '--delete-ghost-image',
    action='store_true',
    help="Lance la suppression de toutes les images fantomes")

# Run the arguments parser
args = parser.parse_args()
    
logger.debug(f"args: {args}")

main(args)