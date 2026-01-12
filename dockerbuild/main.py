# coding=utf-8
from global_vars import *
from lib.gitlab_helper import get_registry_info
from lib.helper import get_changes
from dockerbuild.find_dockerfiles import find_dockerfiles_r
from dockerbuild.create_pipeline import sort_dockerfiles, set_parent_to_is_building, sort_pipeline, pipelines_write_jsonnet, write_jsonnet

logger = logging.getLogger(__name__)

def main(args) :
    #Find the registry of the project 
    registry = get_registry_info(args.token, args.project_id)

    #Create an array with the files changed during commit
    changes = get_changes(args.changes_info_file)

    if(args.generate_jsonnet) :
        if (args.trigger_branch == RECETTE_KEY) :
            args.generate_jsonnet_branch_name = args.trigger_branch

    # Find all Dockerfiles in the current path
    logger.info(f"[General] Scanning {args.path} to find Dockerfiles")
    dockerfiles_to_build = find_dockerfiles_r(args.generate_jsonnet_current_repo, args.path, args.generate_jsonnet_branch_name if(args.generate_jsonnet) else NO_BRANCH, changes, registry, args.trigger_project, args.trigger_changes)
    logger.info(f'Found {len(dockerfiles_to_build)} docker images to build.')

    #####
    # Jsonnet generation to build Docker images
    #####
    if(args.generate_jsonnet):
        job = '[Generate Jsonnet]'
        #
        logger.info(f"{job} Executing script with the following args :")
        logger.info(f"Destination file : {args.generate_jsonnet_destination_file}")
        logger.info(f"Using repository : {args.generate_jsonnet_current_repo}")
        logger.info(f"Using branch : {args.generate_jsonnet_branch_name}")

        dockerfiles_branch_tag = args.generate_jsonnet_branch_name

        sortedRes = sort_dockerfiles(dockerfiles_to_build)
        logger.info(f"{job} Sorted Dockerfiles to handle dependencies !")

        new_sortedRes, to_build_array = set_parent_to_is_building(sortedRes,changes)
        logger.info(f"{job} Set child to build if their parent are !")
        
        if(args.pipeline_source == "schedule") :
            pipelines = sort_pipeline(new_sortedRes)
            
            pipelines_write_jsonnet(pipelines, args.generate_jsonnet_pipeline_folder, args.generate_jsonnet_destination_file, dockerfiles_branch_tag, args.token, args.project_id)
        else :
            trigger_variable = {}
            
            try :
                trigger_variable = json.loads(args.trigger_variables)
            except :
                logger.debug("trigger variable is None")
            
            os.makedirs(os.path.dirname(f"{args.generate_jsonnet_pipeline_folder}/"), exist_ok=True)
            shutil.copy(args.generate_jsonnet_destination_file, f"{args.generate_jsonnet_pipeline_folder}/pipelines.jsonnet")
            write_jsonnet(new_sortedRes, {'mode':"build",'to_build':to_build_array}, f"{args.generate_jsonnet_pipeline_folder}/pipelines.jsonnet", dockerfiles_branch_tag, args.token, args.project_id, trigger_variable)

        logger.info(f"{job} Writed Jsonnet result to file !")


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
# Jsonnet generation to build Docker images
#####
group.add_argument(
    '-g', '--generate-jsonnet', 
    action='store_true',
    help="Générer un fichier Jsonnet (à partir d'un template) contenant toutes les images à construire et les instructions associées")
parser.add_argument(
    '-gdf', '--generate-jsonnet-destination-file', 
    metavar='FILE_PATH', default='.gitlab-ci.jsonnet',
    help="Fichier Jsonnet de destination")
parser.add_argument(
    '-gcr', '--generate-jsonnet-current-repo', 
    metavar='REPO_NAME', default='cicd-docker',
    help="Nom du dépôt git actuel (afin d'identifier les images qui reposent sur un autre dépôt/repo)")
parser.add_argument(
    '-gbn', '--generate-jsonnet-branch-name', 
    metavar='BRANCH_NAME', default=NO_BRANCH,
    help="Nom de la branche git actuelle, à intégrer dans le tag des images Docker")
parser.add_argument(
    '-gpf', '--generate-jsonnet-pipeline-folder', 
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
# Argument to take trigger var if triggered
#####
parser.add_argument(
    '-tgp', '--trigger-project', 
    metavar='PROJECT_TRIGGER_NAME', default='',
    help="Le nom du projet qui trigger la pipeline")

parser.add_argument(
    '-tgb', '--trigger-branch', 
    metavar='BRANCH_TRIGGER_NAME', default='',
    help="Le nom de la branch du projet qui trigger la pipeline")

parser.add_argument(
    '-tgc', '--trigger-changes', 
    metavar='PROJECT_TRIGGER_CHANGES', default='',
    help="Les fichiers modifies du projet qui trigger la pipeline")

parser.add_argument(
    '-tgv', '--trigger-variables', 
    metavar='PROJECT_TRIGGER_VARIABLES', default='',
    help="Les variables envoyés par le trigger")

#####
# Argument to take pipeline source
#####
parser.add_argument(
    '-pips', '--pipeline-source', 
    metavar='CI_PIPELINE_SOURCE', default='',
    help="La source de la pipeline (schedule/trigger ...)")

# Run the arguments parser
args = parser.parse_args()
    
logger.debug(f"args: {args}")

main(args)