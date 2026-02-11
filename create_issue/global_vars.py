# coding=utf-8
from lib.global_vars import *

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
CREATE_ISSUE_LOG_LEVEL_DEFAULT = "INFO"

CREATE_ISSUE_LOG_LEVEL = os.environ.get("CREATE_ISSUE_LOG_LEVEL", CREATE_ISSUE_LOG_LEVEL_DEFAULT).upper()

logging.basicConfig(
    level=getattr(logging, CREATE_ISSUE_LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

#=======================================================#
#=========== Create_issue Global parameters ============#
#=======================================================#

CREATE_ISSUE_ISSUE_MANDATORY_PARAMETER_DEFAULT = ["title", "assignee_username"]
CREATE_ISSUE_ISSUE_MANDATORY_FIELD_DEFAULT = ["title", "assignee_id"]
CREATE_ISSUE_ISSUE_OTHER_FIELD_DEFAULT = ["description", "labels", "milestone_id", "due_date", "issue_type"]
CREATE_ISSUE_META_ISSUE_DEFAULT = '{}'
CREATE_ISSUE_ISSUE_NUMBER_DEFAULT = 1
CREATE_ISSUE_ISSUE_DEADLINE_DEFAULT = 5 

CREATE_ISSUE_ISSUE_MANDATORY_PARAMETER= env.list('CREATE_ISSUE_ISSUE_MANDATORY_PARAMETER',CREATE_ISSUE_ISSUE_MANDATORY_PARAMETER_DEFAULT)
CREATE_ISSUE_ISSUE_MANDATORY_FIELD= env.list('CREATE_ISSUE_ISSUE_MANDATORY_FIELD',CREATE_ISSUE_ISSUE_MANDATORY_FIELD_DEFAULT)
CREATE_ISSUE_ISSUE_OTHER_FIELD= env.list('CREATE_ISSUE_ISSUE_OTHER_FIELD',CREATE_ISSUE_ISSUE_OTHER_FIELD_DEFAULT)
CREATE_ISSUE_META_ISSUE_RAW = os.environ.get('CREATE_ISSUE_META_ISSUE',CREATE_ISSUE_META_ISSUE_DEFAULT)
CREATE_ISSUE_META_ISSUE = json.loads(CREATE_ISSUE_META_ISSUE_RAW)
CREATE_ISSUE_ISSUE_NUMBER= int(os.environ.get('CREATE_ISSUE_ISSUE_NUMBER',CREATE_ISSUE_ISSUE_NUMBER_DEFAULT))
CREATE_ISSUE_ISSUE_DEADLINE = os.environ.get('CREATE_ISSUE_ISSUE_DEADLINE',CREATE_ISSUE_ISSUE_DEADLINE_DEFAULT)