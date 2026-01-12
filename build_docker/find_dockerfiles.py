from global_vars import *
from build_docker.class_pipeline import Parent,Dockerfile
from build_docker.find_dockerfiles_tools import find_info_from_parameters, convert_variables_to_docker_args, find_info_from_changesfile, find_info_from_path, find_info_from_dockerfile, no_build_file_in_folder, check_if_triggered, create_multistage_parents
from lib.gitlab_helper import get_repository_id

logger = logging.getLogger(__name__)

#=======================================================#
#============= Find Dockerfiles Functions ==============#
#=======================================================#

def find_dockerfiles_parameters(info_from_df, info_from_path, triggered_project, trigger_changes, build_branch, subdir, changes, registry):

    dockerfiles = []

    try :
        info_from_parameters_file = find_info_from_parameters(subdir,info_from_df.parent_version_default)
        # Info from parent_versions file : parent_version_full, parent_version_name, parent_version_number
    except Exception as e:
        logger.info(f"Can't get enough information for {info_from_path.image_name}_{info_from_path.image_version_number} image")
    else:
        for info_from_parameters in info_from_parameters_file:
            logger.debug(info_from_parameters)                    

        if(info_from_path != None and info_from_df != None):
            for info_from_parameters in info_from_parameters_file:
                docker_image_tag_separator = DOCKER_IMAGE_TAG_SEPARATOR

                #Find the repository id
                repository_id = get_repository_id(registry,info_from_df.parent_name)

                # Build parent info
                df_parent = Parent(info_from_df.parent_name, info_from_parameters.parent_version['fullname'], info_from_df.parent_external, False, repository_id)
                if(info_from_df.parent_version_replace_with != False):
                    info_from_parameters.parent_version['version_name'] = info_from_df.parent_version_replace_with

                if(info_from_df.image_version_replace == True):
                    info_from_parameters.parent_version['version_number'] = info_from_path.image_version_number
                else:
                    # If image version (IV) is empty (in python, "None")
                    # Build image_version only with parvent version (PV), to get 'image:PV' and avoid 'image:PV_None'
                    if(info_from_parameters.parent_version['version_number'] == None):
                        docker_image_tag_separator = ""
                        info_from_parameters.parent_version['version_number'] = ""

                # Build image_version string
                df_version = f"{info_from_parameters.parent_version['version_name']}{docker_image_tag_separator}{info_from_parameters.parent_version['version_number']}"
                
                multistage_parents = create_multistage_parents(info_from_df.multistage_parents,registry,info_from_parameters.multistage_parents)
                
                is_triggered = False
                # See if triggered
                
                for stage_parent in multistage_parents :
                    if check_if_triggered(stage_parent,triggered_project,trigger_changes) :
                        is_triggered = True
                
                docker_args = convert_variables_to_docker_args(info_from_parameters.variables,build_branch)

                allowed_push = "true"
                if info_from_parameters.no_repo :
                    allowed_push = "false"

                #Find if dockerfile is changed
                is_changed = find_info_from_changesfile(changes,info_from_path.image_name,info_from_path.image_version_number,False)
                # Add new Dockerfile to array
                df_info = Dockerfile(info_from_path.path, info_from_path.image_name, df_parent,multistage_parents, info_from_parameters, df_version, build_branch, is_changed, is_triggered, docker_args, allowed_push) 

                logger.debug(df_info)
                
                if not info_from_parameters.no_build:
                    dockerfiles.append(df_info)             
    
    return dockerfiles

##### Core functions

def find_dockerfiles_r(current_repo, path = ".", build_branch=NO_BRANCH, changes = [], registry = [], triggered_project = "", trigger_changes = ""):
    '''
    Description:
    > Recursively finds all the Dockerfiles under a path

    Parameters:
    - path (string) : Path to the specified Dockerfile
    - debug (boolean) : Enabling/disabling debug display

    Returns:
    - TODO
    '''
    dockerfiles = []
    
    for subdir, dirs, files in os.walk(path):
        for filename in files:
            filepath = subdir + os.sep + filename

            if filepath.endswith(DOCKER_FILE_NAME):
                
                info_from_path = find_info_from_path(filepath)
                # Info from Path : path, file, image_name, image_version_number

                info_from_df = find_info_from_dockerfile(current_repo, filepath)
                # Info from Dockerfile : parent_version_default, parent_version_replace_with, image_version_replace, parent_name, parent_external, dependencies

                logger.debug(info_from_path)
                logger.debug(info_from_df)  

                is_no_build_file = no_build_file_in_folder(subdir)             
                if not is_no_build_file :
                    tmp_dockerfiles = find_dockerfiles_parameters(info_from_df,info_from_path,triggered_project,trigger_changes,build_branch,subdir,changes,registry)             
                    dockerfiles.extend(tmp_dockerfiles)
    
    return dockerfiles