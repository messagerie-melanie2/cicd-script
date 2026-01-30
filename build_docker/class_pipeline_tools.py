# coding=utf-8
from build_docker.global_vars import *
from lib.gitlab_helper import find_tag_in_repository

logger = logging.getLogger(__name__)

#=======================================================#
#================ Classes Function Tools================#
#=======================================================#

##### DTOs classes tools

def add_branch_to_version(parent, branch, token, project_id, trigger_variable):
    new_parent = copy.deepcopy(parent)

    if(new_parent.external == False):
        if(new_parent.is_building == True) :
            new_parent.version = "{0}-{1}".format(new_parent.version, branch)
        else :
            if find_tag_in_repository(token,project_id,new_parent.repository_id,f"{new_parent.version}-{branch}") == False:
                if(branch != RECETTE_KEY and branch != PROD_KEY) :
                    new_parent.version = f"{new_parent.version}-{PREPROD_KEY}"
                elif (branch == RECETTE_KEY or branch == PROD_KEY):
                    new_parent.version = f"{new_parent.version}-{PROD_KEY}"
            else :
                if (branch == RECETTE_KEY):
                    if "CI_PARENT_RECETTE" in trigger_variable:
                        new_parent.version = f"{new_parent.version}-{branch}"
                    else :
                        new_parent.version = f"{new_parent.version}-{PROD_KEY}"
                else :
                    new_parent.version = f"{new_parent.version}-{branch}"
    
    return new_parent

def convert_multistage_parents_version_to_docker_args(multistage_parent, debug):

    docker_args=""
    arg_name = f"stage_{multistage_parent.alias}_version"
    docker_args += f"{DOCKER_BUILD_ARG_OPTION}{arg_name}={multistage_parent.version} "

    return docker_args

def create_job_needs(parent, multistage_parents, mode):
    job_needs = "[{pipeline: '$PARENT_PIPELINE_ID',job: 'convert-jsonnet-to-json',}"

    if mode == "all" :
        job_needs += ",{ job: '" + parent.name + ":" + parent.version + "',optional: true}"
    else :
        if not parent.external and parent.is_building :
            job_needs += ",{ job: '" + parent.name + ":" + parent.version + "',optional: true}"
    
    job_already_here = []
    for multistage_parent in multistage_parents :
        job_name = multistage_parent.name + ":" + multistage_parent.version
        if not multistage_parent.external and multistage_parent.is_building and job_name not in job_already_here:
            job_needs += ",{ job: '" + job_name + "',optional: true}"
            job_already_here.append(job_name)

    job_needs += "]"

    return job_needs