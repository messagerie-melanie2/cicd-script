# coding=utf-8
from lib.global_vars import *

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
TRIGGER_LOG_LEVEL_DEFAULT = "INFO"

TRIGGER_LOG_LEVEL = os.environ.get("TRIGGER_LOG_LEVEL", TRIGGER_LOG_LEVEL_DEFAULT).upper()

logging.basicConfig(
    level=getattr(logging, TRIGGER_LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

#=======================================================#
#============== Trigger Global parameters ==============#
#=======================================================#

#Default values
TRIGGER_URL_MAPPING_DEFAULT = {}
TRIGGER_DEFAULT_BRANCH_DEFAULT = "prod"
TRIGGER_PARAMETERS_FILE_NAME_DEFAULT = "./trigger_parameters.yml"
TRIGGER_DESCRIPTION_VARIABLES_DEFAULT = [{'tag': "--parent-recette",'name':"CI_PARENT_RECETTE"}]

TRIGGER_URL_MAPPING_RAW = os.environ.get('TRIGGER_URL_MAPPING',TRIGGER_URL_MAPPING_DEFAULT)
TRIGGER_URL_MAPPING = json.loads(TRIGGER_URL_MAPPING_RAW)
TRIGGER_DEFAULT_BRANCH = os.environ.get('TRIGGER_DEFAULT_BRANCH',TRIGGER_DEFAULT_BRANCH_DEFAULT)
TRIGGER_PARAMETERS_FILE_NAME = os.environ.get('TRIGGER_PARAMETERS_FILE_NAME',TRIGGER_PARAMETERS_FILE_NAME_DEFAULT)
TRIGGER_DESCRIPTION_VARIABLES_RAW = os.environ.get('TRIGGER_DESCRIPTION_VARIABLES',TRIGGER_DESCRIPTION_VARIABLES_DEFAULT)
TRIGGER_DESCRIPTION_VARIABLES = json.loads(TRIGGER_DESCRIPTION_VARIABLES_RAW)