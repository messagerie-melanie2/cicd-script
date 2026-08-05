from clean_registry.global_vars import *
from lib.gitlab_helper import get_branches, get_tags_in_repository,delete_repository_in_registry,delete_tag_in_repository
from clean_registry.clean_tools import check_if_is_dev_branch, check_if_is_tag_to_keep

logger = logging.getLogger(__name__)

def filter_ghost_tags_with_dev_branch(dockerfiles_to_build,repository,tags):
    ghost_tags_with_dev_branch=[]
    repository_not_present = True

    for tag in tags :
        tag_present = False
        for df in dockerfiles_to_build :
            if repository["name"] == df.name :
                repository_not_present = False
                if df.version in tag["name"]:
                    tag_present = True
        
        if not tag_present :
            ghost_tags_with_dev_branch.append({"repository_id":repository["id"],"repository_name":repository["name"],"name":tag["name"],"image_name":repository["name"] + "_" + tag["name"]})
    
    return ghost_tags_with_dev_branch,repository_not_present

def filter_ghost_tags_with_no_dev_branch(branches,ghost_tags_with_dev_branch):
    ghost_tags_no_dev_branch=[]

    for tag in ghost_tags_with_dev_branch :
        is_dev_tag = False
        for branch in branches:
            if check_if_is_dev_branch(branch):
                if branch["name"] in tag["name"]:
                    is_dev_tag = True
        
        if not is_dev_tag and not check_if_is_tag_to_keep(tag["name"]):
            ghost_tags_no_dev_branch.append(tag)
    
    return ghost_tags_no_dev_branch


def clean_ghost_images(registry,dockerfiles_to_build,token,project_id):
    ghost_repositories = []
    ghost_tags = []

    branches = get_branches(token,project_id)
    logger.debug(f"branches of project : {branches}")
    for repository in registry :
        logger.debug(f"repository : {repository}")

        tags = get_tags_in_repository(token,project_id,repository["id"])
        logger.debug(f"tags : {tags}")

        ghost_tags_with_dev_branch,repository_not_present = filter_ghost_tags_with_dev_branch(dockerfiles_to_build,repository,tags)
        logger.debug(f"ghost_tags_with_dev_branch : {ghost_tags_with_dev_branch}")

        ghost_tags_no_dev_branch = filter_ghost_tags_with_no_dev_branch(branches,ghost_tags_with_dev_branch)
        logger.debug(f"ghost_tags_no_dev_branch : {ghost_tags_no_dev_branch}")

        ghost_tags += ghost_tags_no_dev_branch
        
        if (repository_not_present and len(ghost_tags_no_dev_branch) > 0) or (repository_not_present and len(ghost_tags_with_dev_branch) == 0) :
            ghost_repositories.append(repository)
    
    logger.debug(f"ghost_tags : {ghost_tags_with_dev_branch}")
    logger.debug(f"ghost_repositories : {ghost_repositories}")

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
