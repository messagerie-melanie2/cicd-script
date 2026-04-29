from lib.gitlab_helper import get_registry_info
from build_docker.find_dockerfiles import find_dockerfiles_r
from detect_debt.global_vars import *

logger = logging.getLogger(__name__)
# Ca marche comment le logger ?

def main(args) : 

    # Récupérer les infos des paths dans un projet  *-docker  
    registry = get_registry_info(args.token, args.project_id) # ça dégage
    logger.debug(f"Contenu registry, args.token : {args.token} et args.project_id {args.project_id}") 
    
    # Optimimser la feature pour ne checker que les nouvelles images / les changements dans les commits ?

    logger.info(f"[General] Scanning {args.path} to find Dockerfiles")
     

# Analyse la dette   



# Créer ou modifie l'issue de la dette technique   

# create_issue



# Prendre exemple sur clean-registry


