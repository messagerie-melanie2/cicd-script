# coding=utf-8
from lib.global_vars import *

#=======================================================#
#============= Cleanlog Global parameters ==============#
#=======================================================#

CLEANLOG_STATUS_NO_LOG_DEFAULT = ["skipped","canceled"]
CLEANLOG_WEEKS_LIMIT_DEFAULT = None

CLEANLOG_WEEKS_LIMIT = os.environ.get('CLEANLOG_WEEKS_LIMIT',CLEANLOG_WEEKS_LIMIT_DEFAULT)
CLEANLOG_STATUS_NO_LOG = env.list('CLEANLOG_STATUS_NO_LOG',CLEANLOG_STATUS_NO_LOG_DEFAULT)