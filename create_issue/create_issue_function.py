from create_issue.global_vars import *
from lib.gitlab_helper import create_issue, get_users

logger = logging.getLogger(__name__)

#=======================================================#
#============== Create_issue Functions =================#
#=======================================================#

def check_field(issue, field_to_check) :
    """
    Check if all field needed are on a issue.

    Args:
        issue (dict): The issue json.
        field_to_check (list): List of field to check in the issue.

    Returns:
        check (bool): True if all field are in the issue, False if else.
    """
    check = True
    for mandatory_field in field_to_check :
        if issue.get(mandatory_field) == None :
            check = False
    
    return check

def get_user_id(issue, project_user, multiple_user) :
    """
    Get users ids depending of their username.

    Args:
        issue (dict): The issue json.
        project_user (list): List of all user of the project
        multiple_user (bool): Permit multiple user feature.

    Returns:
        user_id (list): List of all user ids needed.
    """

    assignee_username = issue.get("assignee_username")
    user_id = []
    if assignee_username != None :
        assignee_username = assignee_username.lower().split(",")
        logger.debug(f"assignee_username: {assignee_username}")
        if len(assignee_username) > 1  and not multiple_user:
            logger.error(f"assignee_username must have only one username for issue : {issue}.")
            sys.exit()
        for user in project_user :
            if user.get("username").lower() in assignee_username :
                user_id.append(user.get("id"))
                logger.info(f"User {user.get("username")} found with id : {user.get("id")}")
    
    logger.debug(f"user_id: {user_id}")
    if len(user_id) == 0 : 
        logger.warning(f"No user found with name : {issue.get("assignee_username")}")

    return user_id 

def get_due_date(issue):
    """
    Create a due_date if not given depending of CREATE_ISSUE_ISSUE_DEADLINE variable.

    Args:
        issue (dict): The issue json.

    Returns:
        due_date (date): Date where the issue must be due.
    """
    due_date = issue.get("due_date")
    if due_date == None :
        due_date = datetime.now() + timedelta(days=CREATE_ISSUE_ISSUE_DEADLINE)
        due_date = datetime.strftime(due_date, "%Y-%m-%d")
    
    return due_date

def create_issue_payload(issue, field_to_create):
    """
    Create issue payload to create based of field_to_create list.

    Args:
        issue (dict): The issue json.
        field_to_create (list): List of field to fill in the issue payload.

    Returns:
        issue_payload (dict): Payload needed to create an issue with Gitlab API.
    """
    issue_payload = {}
    for field in field_to_create :
        field_payload = issue.get(field)
        if field_payload != None : 
            issue_payload[field] = field_payload
    
    return issue_payload

def set_and_create_issue(token, project_id, issue, project_user, multiple_user):
    """
    Get issue information given and create it.

    Args:
        token (str): Private access token for the GitLab API.
        project_id (int): ID of the GitLab project to query.
        issue (dict): The issue json given.
        project_user (dict): Dict of List of all user depending of the project
        multiple_user (bool): Permit multiple user feature.

    Returns:
        issues_created,project_user (tuple_dict): Tuple composed of the issue created and an updated version of project_user with new project if necessary.
    """
    new_project_user = project_user.copy()
    issues_created = []
    logger.info("Checking if issue have mandatory field...")
    logger.debug(f"issue : {issue}")
    if check_field(issue, CREATE_ISSUE_ISSUE_MANDATORY_PARAMETER_DEFAULT) :
        logger.info(f"Processing issue...")
        issue_project_id = issue.get("project_id")
        if issue_project_id == None :
            issue["project_id"] = project_id
            issue_project_id = project_id
        
        if new_project_user.get(issue_project_id) == None :
            new_project_user[issue_project_id] = get_users(token, issue_project_id)
        
        issue["due_date"] = get_due_date(issue)
        
        assignee_id = get_user_id(issue, new_project_user[issue_project_id], multiple_user)

        for id in assignee_id :
            user_issue = issue.copy()
            user_issue["assignee_id"] = id
            logger.info("Checking issue with real values...")
            logger.debug(f"issue : {issue}")
            if check_field(user_issue, CREATE_ISSUE_ISSUE_MANDATORY_FIELD_DEFAULT) : 
                issue_payload = create_issue_payload(user_issue, CREATE_ISSUE_ISSUE_MANDATORY_FIELD + CREATE_ISSUE_ISSUE_OTHER_FIELD)
                issues_created.append(create_issue(token, user_issue["project_id"], issue_payload))
            else :
                logger.error(f"Issue ({issue}) don't have all mandatory field : {CREATE_ISSUE_ISSUE_MANDATORY_FIELD_DEFAULT}")
                sys.exit()
    else :
        logger.error(f"Issue ({issue}) don't have all mandatory parameter : {CREATE_ISSUE_ISSUE_MANDATORY_PARAMETER_DEFAULT}")
        sys.exit()

    return issues_created,project_user