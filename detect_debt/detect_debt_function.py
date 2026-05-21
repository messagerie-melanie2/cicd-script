from detect_debt.global_vars import *
from build_docker.create_pipeline import sort_dockerfiles 
from lib.gitlab_helper import get_issues, create_issue, get_issues, update_issue, get_user_id, get_users
from lib.helper import request

logger = logging.getLogger(__name__)

def create_or_update_issue(token, project_id, payload, issue_filter):
    """
    Creates or updates a GitLab issue based on the provided payload.

    If an issue matching the filter already exists, it is updated. Otherwise, a new issue is created.

    Args:
        token (str): Private token used for GitLab authentication.
        project_id (int): ID of the GitLab project.
        payload (dict): Issue fields (title, description, labels, assignee_id).
        issue_filter (dict): Filter used to search for an existing issue.

    Returns:
        None
    """

    logger.info(f"Payload created : {payload}")

    obtained_issues = get_issues(token, project_id, issue_filter)

    if not obtained_issues:
        create_issue(token, project_id, payload)
    else:
        update_issue(token, project_id, obtained_issues[0]["iid"], payload)

def dirty_comparaison(current_tags, latest_tags) -> bool:
    """
    Checks whether the current image version is considered up-to-date via a loose tag comparison.

    A current version may not share the same digest as latest, but if one of its tags starts with
    a latest tag (e.g. "13.4-slim" vs "13.4"), it is considered up-to-date.
    Can be disabled via DETECT_EXTERNAL_DEBT_ACTIVATE_DIRTY_COMPARAISON.

    Args:
        current_tags (list[str]): Tags associated with the current image digest.
        latest_tags (list[str]): Tags associated with the latest image digest.

    Returns:
        bool: True if the current version is considered up-to-date, False otherwise.
    """

    current_version_in_latest = any(
          current_tag.startswith(latest_tag + "-") or current_tag == latest_tag
          for latest_tag in latest_tags
          for current_tag in current_tags
    )
    logger.debug(f"current_version_in_latest : {current_version_in_latest}.")

    return current_version_in_latest

def get_info_from_dockerhub(current_name, current_version, latest = "latest") -> tuple[list, list, list]:
    """
    Fetches tag information for a given image from DockerHub.

    Paginates through DockerHub results until the current version tag is found or all pages are exhausted.

    Args:
        current_name (str): Name of the Docker image (e.g. "python", "nginx").
        current_version (str): Tag of the currently used image version (e.g. "3.11-slim").
        latest (str): Tag considered as the latest reference. Defaults to "latest".

    Returns:
        tuple[list, list, list]: A tuple of (current_tag_results, latest_tag_results, all_results), each a list of tag dicts from DockerHub.
    """

    proxies = {
      "http"  : os.environ.get("HTTP_PROXY"),
      "https" : os.environ.get("HTTPS_PROXY")
    }
    
    current = []
    page_number = 0
    results = []
    obtained_latest = []
   
    if "/" in current_name:
        parts = current_name.split("/")
        current_name = parts[-1]
        if "." in parts[0]:  # registry prefix that we ignore (docker.io)
            namespace = "library"
        else:
            namespace = parts[0]
    else:
        namespace = "library"

    while current == [] and len(results) == 100*page_number:
        # Getting tags from dockerhub
        url = f"https://hub.docker.com/v2/namespaces/{namespace}/repositories/{current_name}/tags?page={page_number+1}&page_size=100" 
        r = request("get", url, proxies=proxies)
        if r == {} :
            logger.error(f"404 Failed to get info from dockerhub for {current_name} {current_version}")
        else :
            try :
                results += r.get("results")
            except Exception as err:
                logger.error(f"Got info from dockerhub but {err} with r : {r}")
        current = [result for result in results if result.get("name") == current_version] 
        page_number += 1

    if results != [] :
        obtained_latest = [result for result in results if result.get("name") == latest]

    return current, obtained_latest, results

def get_external_debt_description(sorted_dockerfiles) -> str:
    """
    Builds the markdown description for the external debt GitLab issue.

    For each external Dockerfile, compares its parent version against DockerHub's latest tags
    and populates two tables: outdated images and images requiring manual review (dirty comparison).

    Args:
        sorted_dockerfiles (list): Output of sort_dockerfiles — sorted_dockerfiles[0] contains external Dockerfiles.

    Returns:
        str: Markdown-formatted description listing outdated and ambiguous external images.
    """

    description = "| Dockerfile | Version actuel | Latest tags |\n|------------|---------------|---------------|\n"
    description_dirty =  "| Dockerfile | Version actuel | Tags correspondants | Latest tags |\n|------------|---------------|---------------|---------------|\n"
    description_404 = "| Dockerfile | Version actuel |\n|------------|---------------|\n"

    for df in sorted_dockerfiles[0]:

        if df.parent.external: # Sanity check, dockerfiles should be external in the first array
            
            current, latest, results = get_info_from_dockerhub(df.parent.name, df.parent.version)
            
            if latest : # Sanity check latest is not empty

                # Getting all the tags corresponding to latest 
                latest_digest = latest[0].get("digest")
                latest_tags = [result.get("name") for result in results if result.get("digest") == latest_digest and result.get("name") != "latest"]

                if current : # Check current is not empty and get all the tags corresponding to current digest else current tag
                    current_digest = current[0].get("digest") 
                    current_tags = [result.get("name") for result in results if result.get("digest") == current_digest]
                else : 
                    current_tags = [df.parent.version]
                    logger.error(f"No tags found for dockerfile {df.parent.name} {df.parent.version}.")

                logger.debug(f"Dockerfile {df.parent.name} {df.parent.version} has latest tags : {latest_tags}")
                logger.debug(f"Dockerfile has current tags : {current_tags}")
                
                # Is the current version up to date or non-conventionally named ?
                if DETECT_EXTERNAL_DEBT_ACTIVATE_DIRTY_COMPARAISON :
                    current_version_in_latest = dirty_comparaison(current_tags, latest_tags)
                else :
                    current_version_in_latest = False

                # Filling the description with latest_tags
                if df.parent.version not in latest_tags and not current_version_in_latest :
                     description += f"{df.path} | {df.parent.version} | {', '.join(latest_tags)}\n"   

                # Filling the description with dirty comparison for human check
                if current_version_in_latest :
                    description_dirty += f"{df.path} | {df.parent.version} | {', '.join(current_tags)} | {', '.join(latest_tags)}\n"   
            else :
                logger.debug(f"No latest tag found for  dockerfile {df.parent.name} {df.parent.version}.")
                # Filling the description with unavailbe image on dockerhub
                description_404 += f"{df.path} | {df.parent.name} {df.parent.version}\n"
    
    description += "## Distrib hors standard\n"
    description += description_dirty
    description += "## 404 Dockerhub API\n"
    description += description_404

    return description

def external_debt(token, project_id, dockerfiles) -> tuple[dict, dict]:
    """
    Orchestrates external debt detection and returns the GitLab issue payload and filter.

    Args:
        token (str): Private token used for GitLab authentication.
        project_id (int): ID of the GitLab project where the issue will be created or updated.
        dockerfiles (list): List of Dockerfile objects found in the scanned repository.

    Returns:
        tuple[dict, dict]: The issue payload and the issue filter.
    """

    sorted_dockerfiles = sort_dockerfiles(dockerfiles)

    logger.info(f"{len(sorted_dockerfiles[0])} external dockerfiles found.")

    description = get_external_debt_description(sorted_dockerfiles)

    logger.info(f"=== External debt found === \n {description}")

    # Creating issue payload
    obtained_users = get_users(token, project_id)

    obtained_users_id = get_user_id(DETECT_EXTERNAL_DEBT_ISSUE_ASSIGNEE_USERNAME, obtained_users, False)

    payload = {
        'title' : DETECT_EXTERNAL_DEBT_ISSUE_TITLE,
        'description' : description, 
        'labels' : DETECT_EXTERNAL_DEBT_ISSUE_LABEL, 
        'assignee_id' : obtained_users_id
    } 

    issue_filter = {'search': DETECT_EXTERNAL_DEBT_ISSUE_TITLE}
    
    return payload, issue_filter

def get_internal_debt_description(dockerfiles) -> str:
    """
    Builds the markdown description for the internal debt GitLab issue.

    For each Dockerfile with an internal parent, compares its parent version against the latest
    version found in the scanned repository and lists outdated images.

    Args:
        dockerfiles (list): List of Dockerfile objects found in the scanned repository.

    Returns:
        str: Markdown-formatted description listing outdated internal images.
    """

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

    return description

def internal_debt(token, project_id, dockerfiles) -> tuple[dict, dict]:
    """
    Orchestrates internal debt detection and returns the GitLab issue payload and filter.

    Args:
        token (str): Private token used for GitLab authentication.
        project_id (int): ID of the GitLab project where the issue will be created or updated.
        dockerfiles (list): List of Dockerfile objects found in the scanned repository.

    Returns:
        tuple[dict, dict]: The issue payload and the issue filter.
    """

    logger.info(f"Found {len(dockerfiles)} Dockerfiles")
    
    description = get_internal_debt_description(dockerfiles) 

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

    return payload, issue_filter
