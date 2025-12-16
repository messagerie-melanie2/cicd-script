# coding=utf-8
from global_vars import *
from gitlab.gitlab_tools import get_registry_info
from process.find_dockerfiles import find_dockerfiles_r
from process.create_pipeline import sort_dockerfiles, set_parent_to_is_building, sort_pipeline, pipelines_write_jsonnet, write_jsonnet
from clean.clean_no_build import clean_ghost_images
from clean.clean_dev import clean_dev_images

def main(args) :
    #Find the registry of the project 
    registry = get_registry_info(args.token, args.project_id, args.debug_enabled)

    #Create an array with the files changed during commit
    changes = []
    try:
            # Read changes.txt
            changes_file = open(args.changes_info_file, 'r')

    except OSError as err:
        if args.debug_enabled :
            print("changes.txt not found...")
        changes_file = []
    
    for line in changes_file :
        changes.append(line) 
        # changes = ["/debian/3.4/Dockerfile",...]

    if(args.generate_jsonnet) :
        if (args.trigger_branch == RECETTE_KEY) :
            args.generate_jsonnet_branch_name = args.trigger_branch

    # Find all Dockerfiles in the current path
    dockerfiles_to_build = find_dockerfiles_r(args.generate_jsonnet_current_repo, args.path, args.generate_jsonnet_branch_name if(args.generate_jsonnet) else NO_BRANCH, changes, registry, args.trigger_project, args.trigger_changes, args.debug_enabled)
    print("\r")
    print('[General] Scanning {0} to find Dockerfiles'.format(args.path))
    print('\tFound {0} docker images to build.'.format(len(dockerfiles_to_build)))

    #####
    # Jsonnet generation to build Docker images
    #####
    if(args.generate_jsonnet):
        job = '[Generate Jsonnet]'
        #
        print("\r\n{0} Executing script with the following args :".format(job))
        print("\r\t{0} : \t {1}".format('Destination file', args.generate_jsonnet_destination_file))
        print("\r\t{0} : \t {1}".format('Using repository', args.generate_jsonnet_current_repo))
        print("\r\t{0} : \t {1}".format('Using branch', args.generate_jsonnet_branch_name))
        print("\r")

        # if we are on main/master branch, we do not add '-branch' to the image tag
        dockerfiles_branch_tag = args.generate_jsonnet_branch_name

        sortedRes = sort_dockerfiles(dockerfiles_to_build, args.debug_enabled)
        print("\r\n{0} Sorted Dockerfiles to handle dependencies !".format(job))

        new_sortedRes, to_build_array = set_parent_to_is_building(sortedRes,changes, args.debug_enabled)
        print("\r\n{0} Set child to build if their parent are !".format(job))
        
        if(args.pipeline_source == "schedule") :
            pipelines = sort_pipeline(new_sortedRes, args.debug_enabled)
            
            pipelines_write_jsonnet(pipelines, args.generate_jsonnet_pipeline_folder, args.generate_jsonnet_destination_file, dockerfiles_branch_tag, args.token, args.project_id, args.debug_enabled)
        else :
            trigger_variable = {}
            
            try :
                trigger_variable = json.loads(args.trigger_variables)
            except :
                if args.debug_enabled :
                    print("trigger variable is None")
            
            os.makedirs(os.path.dirname(f"{args.generate_jsonnet_pipeline_folder}/"), exist_ok=True)
            shutil.copy(args.generate_jsonnet_destination_file, f"{args.generate_jsonnet_pipeline_folder}/pipelines.jsonnet")
            write_jsonnet(new_sortedRes, {'mode':"build",'to_build':to_build_array}, f"{args.generate_jsonnet_pipeline_folder}/pipelines.jsonnet", dockerfiles_branch_tag, args.token, args.project_id, trigger_variable, args.debug_enabled)

        print("\r\n{0} Writed Jsonnet result to file !".format(job))

    #####
    # Finding tags of 'NO_BUILD' Docker images
    #####
    if(args.delete_ghost_image):
        clean_ghost_images(registry,dockerfiles_to_build,args.token, args.project_id,args.debug_enabled)

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
    '-d', '--debug-enabled', 
    metavar='DEBUG', default=False,
    help="Afficher plus de logs lors de l'exécution des fonctions")
parser.add_argument(
    '-p', '--path', 
    metavar='DIR_PATH', default='.',
    help="Choisir le dossier utilisé comme cible pour la recherche des fichiers (Dockerfiles, versions, etc)")

#####
# Testing functions made in this script
#####
group.add_argument(
    '-t', '--test-functions', 
    action='store_true',
    help="Exécuter des tests sur les fonctions définies et utilisées dans ce programme",
    )

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

if args.debug_enabled == 'false' :
    args.debug_enabled = False
elif args.debug_enabled == 'true' :
    args.debug_enabled = True
    
if(args.debug_enabled):
    print(args)

main(args)

# End
print("\r")