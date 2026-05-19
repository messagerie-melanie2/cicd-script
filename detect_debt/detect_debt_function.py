from build_docker.create_pipeline import sort_dockerfiles 
from lib.gitlab_helper import get_issues, create_issue, get_issues, update_issue, get_user_id, get_users
from lib.helper import request
from detect_debt.global_vars import *

logger = logging.getLogger(__name__)

def create_or_update_issue(token, project_id, payload, issue_filter):

    logger.info(f"Payload created : {payload}")

    obtained_issues = get_issues(token, project_id, issue_filter)

    if not obtained_issues:
        create_issue(token, project_id, payload)
    else:
        update_issue(token, project_id, obtained_issues[0]["iid"], payload)

def external_debt(token, project_id, dockerfiles):

    sorted_dockerfiles = sort_dockerfiles(dockerfiles)

    logger.debug(f"Dockerfile architecture : \n \
        path : {sorted_dockerfiles[0][0].path} \n \
        name : {sorted_dockerfiles[0][0].name} \n \
        version : {sorted_dockerfiles[0][0].version} \n \
        parent : {sorted_dockerfiles[0][0].parent} \n \
        parent.name : {sorted_dockerfiles[0][0].parent.name} \n \
        parent.version : {sorted_dockerfiles[0][0].parent.version} \n \
        parent.external : {sorted_dockerfiles[0][0].parent.external}")
    
    logger.info(f"{len(sorted_dockerfiles[0])} external dockerfiles found.")

    http_proxy = os.environ.get("HTTP_PROXY")
    https_proxy = os.environ.get("HTTPS_PROXY")
    proxies = {
      "http"  : http_proxy,
      "https" : https_proxy
    }

    description = "| Dockerfile | Version actuel | Latest tags |\n|------------|---------------|-----------------|\n"
      
    for df in sorted_dockerfiles[0]:

        if df.parent.external: # Sanity check, dockerfiles should be external in the first array
        
            # Getting tags from dockerhub
            url = f"https://hub.docker.com/v2/repositories/library/{df.parent.name}/tags?page=1&page_size=1000" 
            r = request("get", url, proxies=proxies)
            results = r.get("results")

            # Getting "latest" tag and current tag elements
            latest = [result for result in results if result.get("name") == "latest"]
            current = [result for result in results if result.get("name") == df.parent.version] 

            if latest: # Sanity check latest is not empty

                # Getting all the tags corresponding to latest 
                latest_digest = latest[0].get("digest")
                latest_tags = [result.get("name") for result in results if result.get("digest") == latest_digest and result.get("name") != "latest"]

                if current : # Check current is not empty and get all the tags corresponfing to current digest else current tag
                    current_digest = current[0].get("digest") 
                    current_tags = [result.get("name") for result in results if result.get("digest") == current_digest]
                else : 
                    current_tags = [df.parent.version]
                    logger.error(f"No tags found for dockerfile {df.parent.name} {df.parent.version}.")

                logger.debug(f"Dockerfile {df.parent.name} {df.parent.version} has latest tags : {latest_tags}")
                logger.debug(f"Dockerfile has current tags : {current_tags}")

                # Dirty comparison : current_version may not share the same digest as latest,
                # but if it starts with the same version number (e.g. "13.4-slim" vs "13.4"),
                # it is considered up-to-date 
                if DETECT_EXTERNAL_DEBT_ACTIVATE_DIRTY_COMPARAISON :
                    current_version_in_latest = any(
                          current_tag.startswith(latest_tag + "-") or current_tag == latest_tag
                          for latest_tag in latest_tags
                          for current_tag in current_tags
                    )
                    logger.debug(f"current_version_in_latest : {current_version_in_latest}.")

                # Filling the description with latest_tags
                if df.parent.version not in latest_tags and not current_version_in_latest :
                     description += f"{df.path} | {df.parent.version} | {', '.join(latest_tags)}\n"   

            else :
                logger.error(f"No latest tags found for dockerfile {df.parent.name} {df.parent.version}.")

    logger.info(f"=== External debt found === \n {description}")

    # Creating/modifying debt issue
    obtained_users = get_users(token, project_id)

    obtained_users_id = get_user_id(DETECT_EXTERNAL_DEBT_ISSUE_ASSIGNEE_USERNAME, obtained_users, False)

    payload = {
        'title' : DETECT_EXTERNAL_DEBT_ISSUE_TITLE,
        'description' : description, 
        'labels' : DETECT_EXTERNAL_DEBT_ISSUE_LABEL, 
        'assignee_id' : obtained_users_id
    }
    
    issue_filter = {'search': DETECT_EXTERNAL_DEBT_ISSUE_TITLE}

    if DETECT_EXTERNAL_DEBT_ACTIVATE_ISSUE : create_or_update_issue(token, project_id, payload, issue_filter)

def internal_debt(token, project_id, dockerfiles):

    logger.info(f"Found {len(dockerfiles)} Dockerfiles")
    
    description = "| Dockerfile | Parent actuel | Dernière version |\n|------------|---------------|-----------------|\n"

    # Creating a dict of all dockerfiles with their versions
    versions = {}
    for df in dockerfiles:
        if df.name not in versions:
            versions[df.name] = []
        versions[df.name].append(df.path.split('/')[-1])
    logger.debug(f"Versions found : {versions}")

    # Analysing debt 
    for df in dockerfiles:
        # Check only dockerfiles which depend on internal parent
        if not df.parent.external:
            latest = max(versions[df.parent.name])
            logger.debug(f"{df.name} having parent {df.parent.name} {df.parent.version}")
            if df.parent.version.split('_')[-1] < latest :
                logger.debug(f"Found technical debt for {df.name} at {df.path}, using parent {df.parent.name} {df.parent.version} but could be using version {latest}")
                description += f"{df.path} | {df.parent.name} {df.parent.version} | {latest}\n"

    logger.info(f"=== Internal debt found === \n {description}")

    # Creating/modifying debt issue
    obtained_users = get_users(token, project_id)

    obtained_users_id = get_user_id(DETECT_INTERNAL_DEBT_ISSUE_ASSIGNEE_USERNAME, obtained_users, False)

    payload = {
        'title' : DETECT_INTERNAL_DEBT_ISSUE_TITLE,
        'description' : description, 
        'labels' : DETECT_INTERNAL_DEBT_ISSUE_LABEL, 
        'assignee_id' : obtained_users_id
    }
    
    issue_filter = {'search': DETECT_INTERNAL_DEBT_ISSUE_TITLE}

    if DETECT_INTERNAL_DEBT_ACTIVATE_ISSUE : create_or_update_issue(token, project_id, payload, issue_filter)
