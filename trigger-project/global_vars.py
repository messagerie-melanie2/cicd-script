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

#Default values
URL_MAPPING = {"jenkins": {"prod":"https://jenkins-prod.mel.edcs.fr/jenkins-prod/generic-webhook-trigger/invoke","preprod":"https://jenkins-preprod.mel.edcs.fr/jenkins-preprod/generic-webhook-trigger/invoke"}}
DEFAULT_BRANCH = "prod"
TRIGGER_PARAMETERS_FILE_NAME = "./trigger_parameters.yml"
DESCRIPTION_VARIABLES = [{'tag': "--parent-recette",'name':"CI_PARENT_RECETTE"}]