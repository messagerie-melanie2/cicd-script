from lib.global_vars import *

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
DETECT_DEBT_LOG_LEVEL_DEFAULT = "INFO"
DETECT_DEBT_ISSUE_TITLE_DEFAULT = "[Technical debt]"
DETECT_DEBT_ISSUE_LABEL_DEFAULT = "En prod"
DETECT_DEBT_ISSUE_ASSIGNEE_USERNAME_DEFAULT = ""

DETECT_DEBT_LOG_LEVEL = os.environ.get("DETECT_DEBT_LOG_LEVEL", DETECT_DEBT_LOG_LEVEL_DEFAULT).upper()
DETECT_DEBT_ISSUE_TITLE = os.environ.get("DETECT_DEBT_ISSUE_TITLE", DETECT_DEBT_ISSUE_TITLE_DEFAULT)
DETECT_DEBT_ISSUE_LABEL = os.environ.get("DETECT_DEBT_ISSUE_LABEL", DETECT_DEBT_ISSUE_LABEL_DEFAULT)
DETECT_DEBT_ISSUE_ASSIGNEE_USERNAME = os.environ.get("DETECT_DEBT_ISSUE_ASSIGNEE_USERNAME", DETECT_DEBT_ISSUE_ASSIGNEE_USERNAME_DEFAULT)

logging.basicConfig(
    level=getattr(logging, DETECT_DEBT_LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
