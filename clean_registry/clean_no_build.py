from clean_registry.global_vars import *
from lib.gitlab_helper import get_branches, get_tags_in_repository,delete_repository_in_registry,delete_tag_in_repository

logger = logging.getLogger(__name__)

def filter_ghost_tags_with_dev_branch(dockerfiles_to_build,repository,tags):
    ghost_tags_with_dev_branch=[]
    repository_not_present = True

    for tag in tags :
        tag_not_present = True
        for df in dockerfiles_to_build :
            if repository["name"] == df.name :
                repository_not_present = False
                if df.version in tag["name"]:
                    tag_not_present = False
        
        if tag_not_present :
            ghost_tags_with_dev_branch.append({"repository_id":repository["id"],"repository_name":repository["name"],"name":tag["name"],"image_name":repository["name"] + "_" + tag["name"]})
    
    return ghost_tags_with_dev_branch,repository_not_present

def filter_ghost_tags_with_no_dev_branch(branches,ghost_tags_with_dev_branch):
    ghost_tags_no_dev_branch=[]

    for tag in ghost_tags_with_dev_branch :
        is_not_dev_tag = True
        for branch in branches:
            if branch["name"] != PREPROD_KEY and branch["name"] != PROD_KEY and RECETTE_KEY not in tag["name"]:
                if branch["name"] in tag["name"]:
                    is_not_dev_tag = False
        
        if is_not_dev_tag :
            ghost_tags_no_dev_branch.append(tag)
    
    return ghost_tags_no_dev_branch


def clean_ghost_images(registry,dockerfiles_to_build,token,project_id):
    ghost_repositories = []
    ghost_tags = []

    branches = get_branches(token,project_id)

    for repository in registry :
        tags = get_tags_in_repository(token,project_id,repository["id"])

        ghost_tags_with_dev_branch,repository_not_present = filter_ghost_tags_with_dev_branch(dockerfiles_to_build,repository,tags)

        ghost_tags_no_dev_branch = filter_ghost_tags_with_no_dev_branch(branches,ghost_tags_with_dev_branch)

        ghost_tags += ghost_tags_no_dev_branch
        
        if (repository_not_present and len(ghost_tags_no_dev_branch) > 0) or (repository_not_present and len(ghost_tags_with_dev_branch) == 0) :
            ghost_repositories.append(repository)
    
    for ghost_repository in ghost_repositories :
        if ghost_repository["name"] not in REPOSITORIES_WHITELIST :
            logger.info(f"we have to delete {ghost_repository['name']} repository")
            deleted = delete_repository_in_registry(token,project_id,ghost_repository["id"])
            if deleted :
                logger.info(f"{ghost_repository['name']} repository is deleted")
            else :
                logger.warning(f"{ghost_repository['name']} repository couldn't be deleted")
        else :
            logger.info(f"{ghost_repository['name']} repository is whitelisted")
    
    for ghost_tag in ghost_tags :
        if ghost_tag["repository_name"] not in REPOSITORIES_WHITELIST :
            print(f"we have to delete {ghost_tag['image_name']} tag")
            deleted = delete_tag_in_repository(token,project_id,ghost_tag["repository_id"],ghost_tag["name"])
            if deleted :
                logger.info(f"{ghost_tag['image_name']} tag is deleted")
            else :
                logger.warning(f"{ghost_tag['image_name']} tag couldn't be deleted")
        else :
            logger.info(f"{ghost_tag['image_name']} tag is whitelisted")
