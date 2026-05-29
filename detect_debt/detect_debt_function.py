from detect_debt.global_vars import *
from build_docker.create_pipeline import sort_dockerfiles
from lib.gitlab_helper import get_issues, create_issue, update_issue, get_user_id, get_users
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

def wrap_tags(tags, max_len=40) -> str:
    """
    Formats a list of tags into a multi-line string for Markdown table cell rendering.

    Tags are joined with ', ' on each line. A new line is started whenever adding the next
    tag would exceed max_len characters. Lines are separated by ',<br>'.

    Args:
        tags (list[str]): List of tag names to format.
        max_len (int): Maximum character length per line. Defaults to 40.

    Returns:
        str: Formatted string with '<br>'-separated lines, or "" if tags is empty.
    """

    if not tags:
        return ""
    lines, current_line_tags, current_len = [], [], 0
    for tag in tags:
        # +2 accounts for the ', ' separator added between tags on the same line
        add_len = len(tag) + (2 if current_line_tags else 0)
        if current_line_tags and current_len + add_len > max_len:
            lines.append(', '.join(current_line_tags))
            current_line_tags, current_len = [tag], len(tag)
        else:
            current_line_tags.append(tag)
            current_len += add_len
    if current_line_tags:
        lines.append(', '.join(current_line_tags))
    return ',<br>'.join(lines)

def get_info_from_dockerhub(current_service_name, current_tag_name, latest="latest", all_tags_info=None) -> tuple[dict | None, dict | None, dict]:
    """
    Fetches tag information for a given image from DockerHub.

    Paginates through DockerHub results until both the current and latest tags are found
    and at least one named version alias for latest is resolved, or all pages are exhausted.

    Args:
        current_service_name (str): Docker image name (e.g. "python", "bitnami/mariadb-galera").
            Namespace is inferred from the name: "library" for official images, explicit otherwise.
        current_tag_name (str): Tag of the currently used image version (e.g. "3.11-slim").
        latest (str): Tag considered as the latest reference. Defaults to "latest".
        all_tags_info (dict | None): Dict carrying already-fetched tags and pagination state
            ({"tags": [], "last_page_requested": 0}). Pass the result of a previous call to
            resume pagination and avoid redundant requests. Defaults to None (fresh fetch).

    Returns:
        tuple[dict | None, dict | None, dict]: (current_tag_info, latest_tag_info, all_tags_info)
            - current_tag_info: tag dict matching current_tag_name, or None if not found.
            - latest_tag_info: tag dict matching the latest tag, or None if not found.
            - all_tags_info: updated dict with all fetched tags and last page requested.
    """

    proxies = {
      "http": os.environ.get("HTTP_PROXY"),
      "https": os.environ.get("HTTPS_PROXY")
    }

    current_tag_info = None
    latest_tag_info = None

    if not all_tags_info:
        all_tags_info = {
            "tags": [],
            "last_page_requested": 0
        }

    if "/" in current_service_name:
        parts = current_service_name.split("/")
        current_service_name = parts[-1]
        if "." in parts[0]:
            namespace = parts[1] if len(parts) > 2 else "library" # Anticipating cases like docker.io/bitnami/mariadb-galera
        else:
            namespace = parts[0]
    else:
        namespace = "library"

    # Paginate until we have current, latest, and at least one named version alias for latest
    while True:

        url = f"https://hub.docker.com/v2/namespaces/{namespace}/repositories/{current_service_name}/tags?page={all_tags_info['last_page_requested']+1}&page_size=100"
        r = request("get", url, proxies=proxies)
        if r == {}:
            logger.error(f"Failed to get info from dockerhub for {current_service_name} {current_tag_name}")
            break
        try:
            all_tags_info["tags"] += r.get("results")
        except TypeError as err:
            logger.error(f"Got info from dockerhub but {err} with r : {r}")
            break

        current_tag_info = next((elem for elem in all_tags_info["tags"] if elem.get("name") == current_tag_name), None)
        latest_tag_info = next((elem for elem in all_tags_info["tags"] if elem.get("name") == latest), None)

        all_tags_info["last_page_requested"] += 1

        # Exit:
        # condition 1: current and latest found + latest has at least one named version alias (or it's been already 5 requests)
        # condition 2: no more results from dockerhub
        if current_tag_info and latest_tag_info:
            latest_digest = latest_tag_info.get("digest")
            if any(result.get("digest") == latest_digest and result.get("name") != latest for result in all_tags_info["tags"]) or all_tags_info["last_page_requested"] >= 5:
                break
        if len(r.get("results")) != 100:
            break

    return current_tag_info, latest_tag_info, all_tags_info

def get_all_info_from_dockerhub(sorted_dockerfiles) -> dict:
    """
    Builds a shared DockerHub tag cache for all external Dockerfiles.

    Groups requests by image name to avoid redundant API calls: if multiple Dockerfiles
    share the same image (e.g. different versions of "python"), pages already fetched are
    reused and pagination resumes from where it left off.

    Args:
        sorted_dockerfiles (list): Output of sort_dockerfiles — sorted_dockerfiles[0] contains
            external Dockerfiles.

    Returns:
        dict: Mapping image name → all_tags_info dict
            ({"tags": [...], "last_page_requested": N}).
            Images that triggered an API failure have last_page_requested == 0.
    """
    # Optimising requests to dockerhub : constructing a dict with info on all our external dockerfiles
    all_df_info = {}

    for df in sorted_dockerfiles[0]:

        if df.parent.external: # Sanity check, dockerfiles should be external in the first array

            # Service not present at all in our dict
            if df.parent.name not in all_df_info:
                _, _, all_df_info[df.parent.name] = get_info_from_dockerhub(df.parent.name, df.parent.version)

            # Service already requested but got an API fail
            elif all_df_info[df.parent.name]['last_page_requested'] == 0:
                logger.debug(f"Optimisation worked for {df.parent.name} {df.parent.version}, already got on API fail.")

            # Service partially present in our dict but missing info on the specific version
            elif not any(tag.get("name") == df.parent.version for tag in all_df_info[df.parent.name]["tags"]):
                _, _, all_df_info[df.parent.name] = get_info_from_dockerhub(df.parent.name, df.parent.version, all_tags_info = all_df_info[df.parent.name])
                logger.debug(f"Optimisation worked for {all_df_info[df.parent.name]['last_page_requested']} requests on {df.parent.name} {df.parent.version}.")
            else:
                logger.debug(f"Optimisation worked for dockerfile {df.parent.name} {df.parent.version}.")

    return all_df_info

def get_dockerfile_children_paths(dockerfile) -> list[str]:
    """
    Returns the flat list of paths for a Dockerfile and all its descendants (recursive).

    Args:
        dockerfile: A Dockerfile object with a .path (str) and .children (list) attribute.

    Returns:
        list[str]: Paths of the given Dockerfile and all its children, depth-first.
    """
    path = [dockerfile.path]
    for children in dockerfile.children:
        path += get_dockerfile_children_paths(children)

    return path

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

    description_outdated = "| Dockerfile | Version actuel | Latest tags | Enfants concernés |\n|------|------|------|------|\n"
    description_dirty =  "| Dockerfile | Version actuel | Tags correspondants | Latest tags | Enfants concernés |\n|----|----|----|----|----|\n"
    description_failed = "| Dockerfile | Version actuel |\n|----|----|\n"
    description_up_to_date = "| Dockerfile | Version actuel | Latest tags |\n|----|----|----|\n"

    all_df_info = get_all_info_from_dockerhub(sorted_dockerfiles)

    for df in sorted_dockerfiles[0]:

        if df.parent.external: # Sanity check, dockerfiles should be external in the first array

            current_tag_info = next((elem for elem in all_df_info[df.parent.name]["tags"] if elem.get("name") == df.parent.version), None)
            latest_tag_info = next((elem for elem in all_df_info[df.parent.name]["tags"] if elem.get("name") == "latest"), None)

            if latest_tag_info: # Sanity check latest is not empty

                # Getting all the tags corresponding to latest
                latest_digest = latest_tag_info.get("digest")
                latest_tags = [result.get("name") for result in all_df_info[df.parent.name]["tags"] if result.get("digest") == latest_digest and result.get("name") != "latest"]

                if current_tag_info: # Check current_tag_info is not empty and get all the tags corresponding to current digest
                    current_digest = current_tag_info.get("digest")
                    if current_digest is None:
                        logger.error(f"Current dockerfile {df.parent.name} {df.parent.version} has no digest.")
                        current_tags = [df.parent.version]
                    else:
                        logger.debug(f"Current digest for dockerfile {df.parent.name} {df.parent.version} is {current_digest}")
                        current_tags = [result.get("name") for result in all_df_info[df.parent.name]["tags"] if result.get("digest") == current_digest]
                else:
                    current_digest = None
                    current_tags = [df.parent.version]
                    logger.error(f"No tags found for dockerfile {df.parent.name} {df.parent.version}.")

                logger.debug(f"Dockerfile {df.parent.name} {df.parent.version} has latest tags : {latest_tags} and current tags : {current_tags}")

                display_latest = wrap_tags(latest_tags) if latest_tags else "latest"

                # If dockerfile has technical debt
                if current_digest != latest_digest:

                    # Is the current version up to date or non-conventionally named ?
                    if DETECT_EXTERNAL_DEBT_ACTIVATE_DIRTY_COMPARAISON:
                        passes_dirty_comparaison = dirty_comparaison(current_tags, latest_tags)
                    else:
                        passes_dirty_comparaison = False

                    df_children_path = ['- ' + path for child in df.children for path in get_dockerfile_children_paths(child)]
                    display_children_path = '<br>'.join(df_children_path)
                    # Filling the first table for classic technical debt
                    if not passes_dirty_comparaison:
                        description_outdated += f"{df.path} | {df.parent.version} | {display_latest} | {display_children_path}\n"
                    # Filling the dirty comparaison table for human check
                    else:
                        display_current = wrap_tags(current_tags)
                        description_dirty += f"{df.path} | {df.parent.version} | {display_current} | {display_latest} | {display_children_path}\n"

                # Else dockerfile is up to date
                else:
                    description_up_to_date += f"{df.path} | {df.parent.version} | {display_latest}\n"

            else:
                logger.debug(f"No latest tag found for dockerfile {df.parent.name} {df.parent.version}.")
                # Filling the "failed" table
                description_failed += f"{df.path} | {df.parent.name} {df.parent.version}\n"
        else:
            logger.error(f"Dockerfile {df.parent.name} {df.parent.version} is not external but given as one.")

    description = f"## Dette externe ({description_outdated.count('\n')-2})\n"
    description += description_outdated
    description += f"## Equivalent latest ({description_dirty.count('\n')-2})\n"
    description += description_dirty
    description += f"## Dockerhub API fail ({description_failed.count('\n')-2})\n"
    description += description_failed
    if DETECT_EXTERNAL_DEBT_ACTIVATE_UP_TO_DATE_TABLE:
        description += f"## Up to date ({description_up_to_date.count('\n')-2})\n"
        description += description_up_to_date
        newline_count = 12 # Number of lines corresponding to anything but dockerfiles
    else:
        newline_count = 9

    # Sanity check : assuring we treated every dockerfile
    if description.count('\n')-newline_count != len(sorted_dockerfiles[0]):
        logger.error(f"Error : Initially got {len(sorted_dockerfiles[0])} dockerfiles from sorted_dockerfiles() but listed {description.count('\n')-newline_count} in the issue.")

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
        'title': DETECT_EXTERNAL_DEBT_ISSUE_TITLE,
        'description': description,
        'labels': DETECT_EXTERNAL_DEBT_ISSUE_LABEL,
        'assignee_id': obtained_users_id
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
            if df.parent.version.split('_')[-1] < latest:
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
        'title': DETECT_INTERNAL_DEBT_ISSUE_TITLE,
        'description': description,
        'labels': DETECT_INTERNAL_DEBT_ISSUE_LABEL,
        'assignee_id': obtained_users_id
    }

    issue_filter = {'search': DETECT_INTERNAL_DEBT_ISSUE_TITLE}

    return payload, issue_filter
