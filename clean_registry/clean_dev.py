from clean_registry.global_vars import *
from lib.gitlab_helper import get_branches, get_tags_in_repository,delete_tag_in_repository
from clean_registry.clean_tools import check_if_is_tag_to_keep

logger = logging.getLogger(__name__)

def clean_dev_images(registry,token,project_id):
    dev_tags_to_delete = []

    branches = get_branches(token,project_id)
    logger.debug(f"branches of project : {branches}")

    for repository in registry :
        logger.debug(f"repository : {repository}")
        tags = get_tags_in_repository(token,project_id,repository["id"])
        logger.debug(f"tags : {tags}")
        for tag in tags :
            is_current_dev_tag = False
            for branch in branches:
                if branch["name"] in tag["name"]:
                    is_current_dev_tag = True

            if check_if_is_tag_to_keep(tag["name"]):
                is_current_dev_tag = True
            
            if not is_current_dev_tag :
                dev_tags_to_delete.append({"repository_id":repository["id"],"repository_name":repository["name"],"name":tag["name"],"image_name":repository["name"] + "_" + tag["name"]})

    logger.debug(f"dev_tags_to_delete: {dev_tags_to_delete}")
    #Regex : Need 1.0-branch and not only 1.0
    #filtered_dev_tags_to_delete = [tag for tag in dev_tags_to_delete if re.search(r"-[^\s]+$", tag["name"].split(DOCKER_IMAGE_TAG_SEPARATOR)[-1])]

    for tag in dev_tags_to_delete :
        if tag["repository_name"] not in REPOSITORIES_WHITELIST :
            logger.info(f"DEV : we have to delete {tag['image_name']} tag")
            #deleted = delete_tag_in_repository(token,project_id,tag["repository_id"],tag["name"])
            #if deleted :
                #logger.info(f"{tag['image_name']} tag is deleted")
            #else :
                #logger.warning(f"{tag['image_name']} tag couldn't be deleted")
        else :
            logger.info(f"{tag['image_name']} tag is whitelisted")
