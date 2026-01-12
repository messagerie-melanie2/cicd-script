# coding=utf-8
from lib.global_vars import *

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
CLEAN_LOG_LEVEL_DEFAULT = "INFO"

CLEAN_LOG_LEVEL = os.environ.get("CLEAN_LOG_LEVEL", CLEAN_LOG_LEVEL_DEFAULT).upper()

logging.basicConfig(
    level=getattr(logging, CLEAN_LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

#=======================================================#
#============= Cleanlog Global parameters ==============#
#=======================================================#

CLEANLOG_STATUS_NO_LOG_DEFAULT = ["skipped","canceled"]
CLEANLOG_WEEKS_LIMIT_DEFAULT = None

CLEANLOG_WEEKS_LIMIT = os.environ.get('CLEANLOG_WEEKS_LIMIT',CLEANLOG_WEEKS_LIMIT_DEFAULT)
CLEANLOG_STATUS_NO_LOG = env.list('CLEANLOG_STATUS_NO_LOG',CLEANLOG_STATUS_NO_LOG_DEFAULT)