# coding=utf-8
from lib.global_vars import *

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
SETUP_CI_JOB_URL = os.environ.get('CI_JOB_URL',"")
SETUP_LOG_LEVEL_DEFAULT = "INFO"
SETUP_GITLAB_TOKEN_NAME_DEFAULT = "CICD_GITLAB_ADMIN_TOKEN"
SETUP_GITLAB_CI_CONFIG_PATH_DEFAULT = ".gitlab-ci.yml@snum/detn/gmcd/cicd/cicd-yaml"
SETUP_GITLAB_ACCOUNT_USERNAME_DEFAULT = "admin.gitlab"
SETUP_CICD_CONFIGURATION_PATH_VARIABLE_NAME_DEFAULT = "CICD_CONFIGURATION_PATH"
SETUP_CHANNEL_URL_DEFAULT = ""
SETUP_SCHEDULE_TYPE_DEFAULT = """{
    "cleanlog": 
    {
        "description": "[rotate log] Schedule de rotation de log", 
        "cron": "0 0 */5 * *", 
        "cron_timezone": "Europe/Paris",
        "variables":
        {
            "CLEANLOG_WEEKS_LIMIT" : 2,
            "CI_COMMIT_MESSAGE": "[cleanlog] ci-clean-log "
        }
    }
}"""
SETUP_SCHEDULE_MANDATORY_DEFAULT = ["cleanlog"]

SETUP_ACCEPTED_STATUS_CODE = [200,201,202]
SETUP_LOG_LEVEL = os.environ.get("SETUP_LOG_LEVEL", SETUP_LOG_LEVEL_DEFAULT).upper()
SETUP_GITLAB_TOKEN_NAME = os.environ.get('SETUP_GITLAB_TOKEN_NAME',SETUP_GITLAB_TOKEN_NAME_DEFAULT)
SETUP_GITLAB_CI_CONFIG_PATH = os.environ.get('SETUP_GITLAB_CI_CONFIG_PATH',SETUP_GITLAB_CI_CONFIG_PATH_DEFAULT)
SETUP_GITLAB_ACCOUNT_USERNAME = os.environ.get('SETUP_GITLAB_ACCOUNT_USERNAME',SETUP_GITLAB_ACCOUNT_USERNAME_DEFAULT)
SETUP_CICD_CONFIGURATION_PATH_VARIABLE_NAME = os.environ.get('SETUP_CICD_CONFIGURATION_PATH_VARIABLE_NAME',SETUP_CICD_CONFIGURATION_PATH_VARIABLE_NAME_DEFAULT)
SETUP_CICD_CONFIGURATION_PATH = os.environ.get(SETUP_CICD_CONFIGURATION_PATH_VARIABLE_NAME, '')
SETUP_CHANNEL_URL = os.environ.get('SETUP_CHANNEL_URL',SETUP_CHANNEL_URL_DEFAULT)
SETUP_SCHEDULE_TYPE_RAW = os.environ.get('SETUP_SCHEDULE_TYPE',SETUP_SCHEDULE_TYPE_DEFAULT)
SETUP_SCHEDULE_TYPE = json.loads(SETUP_SCHEDULE_TYPE_RAW)
SETUP_SCHEDULE_MANDATORY = env.list('SETUP_SCHEDULE_MANDATORY',SETUP_SCHEDULE_MANDATORY_DEFAULT)

logging.basicConfig(
    level=getattr(logging, SETUP_LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

#=======================================================#
#============== Trigger Global parameters ==============#
#=======================================================#

#Default values
SETUP_TRIGGER_FOLDER_PATH_DEFAULT = "trigger-project/setup/"
SETUP_TRIGGER_FILE_ENDSWITH_DEFAULT = "triggers.yml"
SETUP_TRIGGER_DESCRIPTION_DEFAULT = "Trigger cree par L'administrateur"
SETUP_TRIGGER_GITLAB_VARIABLE_TRIGGER_KEY_DEFAULT = "TRIGGER_TOKEN"
SETUP_TRIGGER_JENKINS_TRIGGER_TOKEN_NAME_DEFAULT = "JENKINS_TRIGGER_TOKEN"

SETUP_TRIGGER_FOLDER_PATH = os.environ.get('SETUP_TRIGGER_FOLDER_PATH',SETUP_TRIGGER_FOLDER_PATH_DEFAULT)
SETUP_TRIGGER_FILE_ENDSWITH = os.environ.get('SETUP_TRIGGER_FILE_ENDSWITH',SETUP_TRIGGER_FILE_ENDSWITH_DEFAULT)
SETUP_TRIGGER_DESCRIPTION = os.environ.get('SETUP_TRIGGER_DESCRIPTION',SETUP_TRIGGER_DESCRIPTION_DEFAULT)
SETUP_TRIGGER_GITLAB_VARIABLE_TRIGGER_KEY = os.environ.get('SETUP_TRIGGER_GITLAB_VARIABLE_TRIGGER_KEY',SETUP_TRIGGER_GITLAB_VARIABLE_TRIGGER_KEY_DEFAULT)
SETUP_TRIGGER_JENKINS_TRIGGER_TOKEN_NAME = os.environ.get('SETUP_TRIGGER_JENKINS_TRIGGER_TOKEN_NAME',SETUP_TRIGGER_JENKINS_TRIGGER_TOKEN_NAME_DEFAULT)

#=======================================================#
#=============== Build Global parameters ===============#
#=======================================================#
SETUP_BUILD_FOLDER_PATH_DEFAULT = "build-docker/setup/"
SETUP_BUILD_FILE_ENDSWITH_DEFAULT = "build.yml"
SETUP_BUILD_TOKEN_NAME_DEFAULT = "CICD_API_TOKEN"
SETUP_BUILD_TOKEN_SCOPE_DEFAULT = ["api","read_api","read_repository","write_repository","read_registry","write_registry"]
SETUP_BUILD_TOKEN_ACCESS_LEVEL_DEFAULT = 40
SETUP_BUILD_ENABLE_BUILD_VARIABLE_NAME_DEFAULT = "ENABLE_BUILD"
SETUP_BUILD_DOCKERHUB_TOKEN_VARIABLE_NAME_DEFAULT = "DOCKERHUB_TOKEN"
SETUP_BUILD_DEPLOY_TOKEN_VARIABLE_NAME_DEFAULT = "DEPLOY_TOKEN"
SETUP_BUILD_SCHEDULE_TYPE_DEFAULT = """{
    "buildall": 
    {
        "description": "Daily rebuild for containers images (security updates)", 
        "cron": "0 20 * * *", 
        "cron_timezone": "Europe/Paris",
        "variables":
        {
            "CI_COMMIT_MESSAGE": "[buildall] Daily rebuild - ci-all ci-check-before-push"
        }
    },
    "cleanghostimage":
    {
        "description": "Daily cleaning for containers images (nobuild images)", 
        "cron": "0 2 * * *", 
        "cron_timezone": "Europe/Paris",
        "variables":
        {
            "CI_COMMIT_MESSAGE": "[cleanghostimage] Daily cleaning 'NO_BUILD' - ci-clean-nobuild"
        }
    },
    "cleandevimage":
    {
        "description": "Daily cleaning for containers images (dev images)", 
        "cron": "30 1 * * *", 
        "cron_timezone": "Europe/Paris",
        "variables":
        {
            "CI_COMMIT_MESSAGE": "[cleandevimage] Daily cleaning 'DEV' - ci-clean-dev"
        }
    }
}"""
SETUP_BUILD_MANDATORY_ALLOWLIST_DEFAULT = {}

SETUP_BUILD_FOLDER_PATH = os.environ.get('SETUP_BUILD_FOLDER_PATH',SETUP_BUILD_FOLDER_PATH_DEFAULT)
SETUP_BUILD_FILE_ENDSWITH = os.environ.get('SETUP_BUILD_FILE_ENDSWITH',SETUP_BUILD_FILE_ENDSWITH_DEFAULT)
SETUP_BUILD_TOKEN_NAME = os.environ.get('SETUP_BUILD_TOKEN_NAME',SETUP_BUILD_TOKEN_NAME_DEFAULT)
SETUP_BUILD_TOKEN_SCOPE = os.environ.get('SETUP_BUILD_TOKEN_SCOPE',SETUP_BUILD_TOKEN_SCOPE_DEFAULT)
SETUP_BUILD_TOKEN_ACCESS_LEVEL = env.list('SETUP_BUILD_TOKEN_ACCESS_LEVEL',SETUP_BUILD_TOKEN_ACCESS_LEVEL_DEFAULT)
SETUP_BUILD_ENABLE_BUILD_VARIABLE_NAME = os.environ.get('SETUP_BUILD_ENABLE_BUILD_VARIABLE_NAME',SETUP_BUILD_ENABLE_BUILD_VARIABLE_NAME_DEFAULT)
SETUP_BUILD_DOCKERHUB_TOKEN_VARIABLE_NAME = os.environ.get('SETUP_BUILD_DOCKERHUB_TOKEN_VARIABLE_NAME',SETUP_BUILD_DOCKERHUB_TOKEN_VARIABLE_NAME_DEFAULT)
SETUP_BUILD_DEPLOY_TOKEN_VARIABLE_NAME = os.environ.get('SETUP_BUILD_DEPLOY_TOKEN_VARIABLE_NAME',SETUP_BUILD_DEPLOY_TOKEN_VARIABLE_NAME_DEFAULT)
SETUP_BUILD_DOCKERHUB_TOKEN = os.environ.get(SETUP_BUILD_DOCKERHUB_TOKEN_VARIABLE_NAME, '')
SETUP_BUILD_DEPLOY_TOKEN = os.environ.get(SETUP_BUILD_DEPLOY_TOKEN_VARIABLE_NAME, '')
SETUP_BUILD_SCHEDULE_TYPE_RAW = os.environ.get('SETUP_BUILD_SCHEDULE_TYPE',SETUP_BUILD_SCHEDULE_TYPE_DEFAULT)
SETUP_BUILD_SCHEDULE_TYPE = json.loads(SETUP_BUILD_SCHEDULE_TYPE_RAW)
SETUP_BUILD_MANDATORY_ALLOWLIST = env.json('SETUP_BUILD_MANDATORY_ALLOWLIST',SETUP_BUILD_MANDATORY_ALLOWLIST_DEFAULT)