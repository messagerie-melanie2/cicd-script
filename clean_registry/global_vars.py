from lib.global_vars import *

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
CLEAN_REGISTRY_LOG_LEVEL_DEFAULT = "INFO"
NO_BRANCH_DEFAULT = "nobranch"
PREPROD_KEY_DEFAULT = "preprod"
PROD_KEY_DEFAULT = "prod"
RECETTE_KEY_DEFAULT = "recette"
REPOSITORIES_WHITELIST_DEFAULT = []

CLEAN_REGISTRY_LOG_LEVEL = os.environ.get("CLEAN_REGISTRY_LOG_LEVEL", CLEAN_REGISTRY_LOG_LEVEL_DEFAULT).upper()
NO_BRANCH = os.environ.get('NO_BRANCH',NO_BRANCH_DEFAULT)
PREPROD_KEY = os.environ.get('PREPROD_KEY',PREPROD_KEY_DEFAULT)
PROD_KEY = os.environ.get('PROD_KEY',PROD_KEY_DEFAULT)
RECETTE_KEY = os.environ.get('RECETTE_KEY',RECETTE_KEY_DEFAULT)
REPOSITORIES_WHITELIST = env.list("REPOSITORIES_WHITELIST",REPOSITORIES_WHITELIST_DEFAULT)

logging.basicConfig(
    level=getattr(logging, CLEAN_REGISTRY_LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)