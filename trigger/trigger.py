# coding=utf-8
from trigger.global_vars import *
from lib.helper import request, add_argument_to_conf

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
# GITLAB_REPO = "https://gitlab-forge.din.developpement-durable.gouv.fr"
# JENKINS_URL = {"prod":"https://jenkins-prod.mel.edcs.fr/jenkins-prod/generic-webhook-trigger/invoke","preprod":"https://jenkins-preprod.mel.edcs.fr/jenkins-preprod/generic-webhook-trigger/invoke"}
# TRIGGER_PARAMETERS_FILE_NAME = "./trigger_parameters.yml"
# DESCRIPTION_VARIABLES = [{'tag': "--parent-recette",'name':"CI_PARENT_RECETTE"}]

#=======================================================#
#======================== Main =========================#
#=======================================================#

def get_changes(commit_before_sha, commit_sha):
    changes = ""
    #Launch a git diff
    try :
        changes = subprocess.check_output(['git','diff','--name-only',commit_before_sha,commit_sha]).decode(sys.stdout.encoding)
        changes = ' '.join(changes.splitlines())
    except subprocess.CalledProcessError as err:
        logging.info(f"Git diff failed...({err})")
    else :
        logging.debug(f"Changed files : {changes}")

    return changes

def read_trigger_parameters_local_file():
    trigger_parameters_local_file = {}
    try:
        with open(TRIGGER_PARAMETERS_FILE_NAME, 'r') as trigger_parameters:
            try:
                trigger_parameters_local_file = yaml.safe_load(trigger_parameters)
            except yaml.YAMLError as exc:
                logging.debug(f"{TRIGGER_PARAMETERS_FILE_NAME} file cannot be load...({exc})")
    except Exception as e:
        logging.debug(f"{TRIGGER_PARAMETERS_FILE_NAME} file not found...({e})")
    
    return trigger_parameters_local_file

def add_local_file_to_config(config, trigger_parameters_local_file) :
    new_config = config.copy()
    for project in trigger_parameters_local_file :
        project_name = project.get('name')
        project_type = project.get('type')
        project_config = new_config.get(project["name"])
        if project_config != None :
            logging.debug(f"{project_name} in trigger_parameters.yml, adding new arguments to config...")
            project_config = project_config | add_argument_to_conf(project, SETUP_TRIGGER_ARGUMENTS, "all")
            project_config = project_config | add_argument_to_conf(project, SETUP_TRIGGER_ARGUMENTS, project_type)
            new_config[str(project_name)] = new_config[str(project_name)] | project_config
        else : 
            logging.debug(f"{project_name} not in trigger_parameters.yml")
    
    return new_config

def check_if_branch_can_trigger(project_name, project_config, branch) :
    branch_can_trigger = False
    branchs_only_trigger = project_config.get("branchs_only_trigger")

    if branchs_only_trigger == None :
        branch_can_trigger = True
    else :
        if branch in branchs_only_trigger :
            branch_can_trigger = True
    
    if not branch_can_trigger :
        logging.info(f"{branch} branch is not in branchs_only_trigger : {branchs_only_trigger} for project {project_name}, trigger will not be launched")

    return branch_can_trigger

def check_if_file_can_trigger(project_name, project_config, changes) :
    file_can_trigger = False
    trigger_files = project_config.get("trigger_files")

    if trigger_files == None :
        file_can_trigger = True
    else :
        changes_list = changes.split(" ")
        for change in changes_list :
            for file in trigger_files :
                if fnmatch.fnmatch(change,'*' + file + '*') :
                    file_can_trigger = True
    
    if not file_can_trigger :
        logging.info(f"{changes} changes is not in trigger_files : {trigger_files} for project {project_name}, trigger will not be launched")

    return file_can_trigger

def get_mapped_branch(initial_branch, project_config) :
    branchs_mapping = project_config.get("branchs_mapping")
    mapped_branch = initial_branch

    if branchs_mapping != None :
        mapping = branchs_mapping.get("branch")
        if mapping != None :
            mapped_branch = mapping
            logging.info(f"branch {mapped_branch} will be triggered")
        else : 
            logging.debug(f"branch {initial_branch} not in branchs_mapping")
    else : 
        logging.debug("branchs_mapping not in config")
    
    return mapped_branch

def create_payload(project_name, project_config, trigger_project, mapped_branch, initial_branch, description, changes):
    project_type = project_config.get("type")
    trigger_token = os.getenv(project_config.get("token_name"))

    logging.info("Creating payload...")
    data = {}

    if project_type == "gitlab" :
        focus_trigger = project_config.get("focus_trigger")
        variables_json = {}
        for variable in DESCRIPTION_VARIABLES :
            if variable["tag"] in description :
                variables_json[variable["name"]] = True
        
        data["token"] = trigger_token
        data["ref"] = mapped_branch
        data["variables[CI_PROJECT_TRIGGER]"] = trigger_project
        data["variables[CI_BRANCH_TRIGGER]"] = initial_branch
        data["variables[TRIGGER_DESCRIPTION]"] = description
        data["variables[TRIGGER_VARIABLES]"] = f"{variables_json}"
        if focus_trigger :
            data["variables[CI_CHANGES_TRIGGER]"] = changes
        
    elif project_type == "jenkins" :
        data["pipeline_name"] = project_name
        additional_params = project_config.get("additional_params")
        if additional_params == None :
            logging.debug("additional_params not in config")
        else : 
            data["additional_params"] = additional_params

    logging.info(f"Payload created : {data}")

    return data

def create_url(project_config, mapped_branch, initial_branch) :
    project_type = project_config.get("type")
    url = ""

    url_mapping = URL_MAPPING.get(project_type)
    if url_mapping != None :
        url = url_mapping.get(mapped_branch)
        if url == None :
            logging.warning(f"branch {initial_branch} not in URL_MAPPING of project type {project_type}. Branch {DEFAULT_BRANCH} will be taken by default")
            url = url_mapping.get(DEFAULT_BRANCH)
    else :
        logging.debug(f"Project type {project_type} doesn't have url_mapping.")
    
    if project_type == "gitlab" :
        url = GITLAB_REPO + '/api/v4/projects/' + str(project_config.get("id"))   + '/trigger/pipeline'
    
    return url

def create_request_auth(project_config, token):
    project_type = project_config.get("type")
    request_auth = {}
    if project_type == "gitlab" :
        request_auth['auth']=('gitlab-ci-token', token)
    if project_type == "jenkins" :
        trigger_token = os.getenv(project_config.get("token_name"))
        request_auth['headers']= {"token": trigger_token}
    
    return request_auth
    

def trigger(project_name, project_config, trigger_project, branch, description, changes, token):
    if check_if_branch_can_trigger(project_name, project_config, branch) :
        if check_if_file_can_trigger(project_name, project_config, changes) :
            logging.info(f"Launch triggering process of {project_name} project")
            mapped_branch = get_mapped_branch(branch, project_config)
            data = create_payload(project_name, project_config, trigger_project, mapped_branch, branch, description, changes)
            url = create_url(project_config, mapped_branch, branch)
            request_auth = create_request_auth(project_config, token)
            response = request("post",url, headers=request_auth.get("headers"), auth=request_auth.get("auth"), data=data)
            logging.debug(f"Response : {response}")

def main(args):
    #Leave proxy
    os.environ["http_proxy"]=""
    os.environ["HTTP_PROXY"]=""
    os.environ["https_proxy"]=""
    os.environ["HTTPS_PROXY"]=""

    trigger_config = env.json(TRIGGER_VARIABLE_CONFIGURATION_KEY_DEFAULT, {})
    trigger_parameters_local_file = read_trigger_parameters_local_file()
    changes = get_changes(args.commit_before_sha,args.commit_sha,args.debug_enabled)

    for project_name,project_config in trigger_config.items() :
        project_config = add_local_file_to_config(project_config, trigger_parameters_local_file)
        trigger(project_name, project_config, args.project, args.branch, args.description, changes, args.token)

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser
parser = argparse.ArgumentParser(
    prog='CICD Python Helper',
    description="Programme permettant de gérer les logs/artifacts des projets gitlab")

parser.add_argument(
    '-tok', '--token', 
    metavar='TOKEN', default=' ',
    help="Token pour accéder à gitlab")
parser.add_argument(
    '-p', '--project', 
    metavar='PROJECT_NAME', default=' ',
    help="Nom du projet qui trigger")
parser.add_argument(
    '-b', '--branch', 
    metavar='BRANCH', default=' ',
    help="Branche qui trigger")
parser.add_argument(
    '-desc', '--description', 
    metavar='DESCRIPTION', default=' ',
    help="Decription du trigger")
parser.add_argument(
    '-cbs', '--commit-before-sha', 
    metavar='COMMIT_BEFORE_SHA', default=' ',
    help="Sha du commit précedent")
parser.add_argument(
    '-cs', '--commit-sha', 
    metavar='COMMIT_SHA', default=' ',
    help="Sha du commit actuelle")

# Run the arguments parser
args = parser.parse_args()

main(args)

# End
print("\r")