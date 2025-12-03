# coding=utf-8
import argparse
import requests
import os
import yaml
import json
from environs import Env

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
env = Env()

#Default values
TRIGGER_CHANNEL_URL_DEFAULT = "https://tchap-bot.mel.e2.rie.gouv.fr/api/webhook/post/VaUQRGFvb5WhklqC6VYmXSlmLKXrcSTbRmoefdzkAbjvh4yXkOqMGZtSsgCsC50bjt0rSyBn1PqWByTirXOYmwhdJMTZfKxnBGUt"
GITLAB_CI_CONFIG_PATH_DEFAULT = ".gitlab-ci.yml@snum/detn/gmcd/cicd/cicd-yaml"
GITLAB_ACCOUNT_USERNAME_DEFAULT = "jenkins.inframel"
TRIGGER_DESCRIPTION_DEFAULT = "Trigger cree par Jenkins"
TRIGGER_ARGUMENTS_DEFAULT = {'all': 'trigger_files,branchs_only_trigger,branchs_mapping', 'gitlab': 'focus_trigger', 'jenkins': 'additional_params,token_name'}
GITLAB_VARIABLE_TRIGGER_KEY_DEFAULT = "TRIGGER_TOKEN"
JENKINS_TRIGGER_TOKEN_NAME_DEFAULT = "JENKINS_TRIGGER_TOKEN"
GITLAB_VARIABLE_TRIGGER_CONFIGURATION_KEY_DEFAULT = "GITLAB_TRIGGER_CONFIGURATION"
JENKINS_VARIABLE_TRIGGER_CONFIGURATION_KEY_DEFAULT = "JENKINS_TRIGGER_CONFIGURATION"

GITLAB_URL = os.environ.get('GITLAB_PROTOCOL',"https://") + os.environ.get('GITLAB_DOMAIN',"")
TRIGGER_CHANNEL_URL = os.environ.get('TRIGGER_CHANNEL_URL',TRIGGER_CHANNEL_URL_DEFAULT)
GITLAB_CI_CONFIG_PATH = os.environ.get('GITLAB_CI_CONFIG_PATH',GITLAB_CI_CONFIG_PATH_DEFAULT)
GITLAB_ACCOUNT_USERNAME = os.environ.get('GITLAB_ACCOUNT_USERNAME',GITLAB_ACCOUNT_USERNAME_DEFAULT)
TRIGGER_DESCRIPTION = os.environ.get('TRIGGER_DESCRIPTION',TRIGGER_DESCRIPTION_DEFAULT)
TRIGGER_ARGUMENTS = env.json('TRIGGER_ARGUMENTS',TRIGGER_ARGUMENTS_DEFAULT)
GITLAB_VARIABLE_TRIGGER_KEY = os.environ.get('GITLAB_VARIABLE_TRIGGER_KEY',GITLAB_VARIABLE_TRIGGER_KEY_DEFAULT)
JENKINS_TRIGGER_TOKEN_NAME = os.environ.get('JENKINS_TRIGGER_TOKEN_NAME',JENKINS_TRIGGER_TOKEN_NAME_DEFAULT)
CI_JOB_URL = os.environ.get('CI_JOB_URL',"")
GITLAB_VARIABLE_TRIGGER_CONFIGURATION_KEY = os.environ.get('GITLAB_VARIABLE_TRIGGER_CONFIGURATION_KEY',GITLAB_VARIABLE_TRIGGER_CONFIGURATION_KEY_DEFAULT)
JENKINS_VARIABLE_TRIGGER_CONFIGURATION_KEY = os.environ.get('JENKINS_VARIABLE_TRIGGER_CONFIGURATION_KEY',JENKINS_VARIABLE_TRIGGER_CONFIGURATION_KEY_DEFAULT)

#=======================================================#
#======================== Main =========================#
#=======================================================#

def request(mode, url = '', headers = None, payload_data = None, payload_json = None, files = None , debug = False):
    response = {}
    try :
        r = requests.Response()
        match mode:
            case "get":
                r = requests.get(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case "post":
                r = requests.post(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case "put":
                r = requests.put(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case "patch":
                r = requests.patch(url=url, headers=headers, data=payload_data, json = payload_json, files=files)
            case _:
                print("request mode not supported")  
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if debug : 
            print("Http Error:",err)
        print(f"Request failed : {r.json()}")
    else :
        response = r.json()
    
    return response
    

def send_message(message, debug = False):
    if TRIGGER_CHANNEL_URL != "" :
        payload = {
            'message': message,
            'message_raw': message
        }
        request("post",TRIGGER_CHANNEL_URL, payload_json=payload, debug=debug)

def read_setup_files(folder_path, debug = False):
    all_setup = []
    my_path = os.path.abspath(os.path.dirname(__file__))
    my_project_path = my_path.split("cicd-script")[0]
    setup_path = os.path.join(my_project_path, folder_path)
    for subdir, dirs, files in os.walk(setup_path):
        for filename in files:
            filepath = subdir + os.sep + filename
            if filepath.endswith("triggers.yml"):
                with open(filepath, 'r') as setup_file:
                    try:
                        setup_yaml = yaml.safe_load(setup_file)
                    except yaml.YAMLError as exc:
                        if debug :
                            print("Couldn't load yaml for {0} file...".format(setup_path))
                            print(exc)
                    else :
                        all_setup = all_setup + setup_yaml
    return all_setup

def set_config_path(token, all_setup, debug = False):
    files = {
        'ci_config_path': (None, GITLAB_CI_CONFIG_PATH),
    }
    headers = {"PRIVATE-TOKEN": token}

    for project_to_trigger in all_setup :
        projects_to_setup = project_to_trigger.get("projects")
        for project in projects_to_setup :
            project_id = project.get("id")
            if project.get("change_ci") != False :
                if project_id == 27032 :
                    print(f"Setting ci config path of {project.get('name')} project")
                    url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
                    request("put", url, headers, files=files, debug=debug)

def config_trigger_token(project, headers, files, debug = False):
    trigger_token = ""
    if project.get("type") == "gitlab" :
        project_name = project.get('name')
        print(f"Setting Trigger token of {project_name} project")
        project_to_trigger_id = project.get("id")

        print(f"Getting Trigger tokens of {project_name} project")
        url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/triggers"
        project_tokens = request("get", url, headers, debug=debug)
        if debug :
            print(project_tokens)

        trigger_token_already_created = False

        for token_info in project_tokens :
            if token_info.get("owner").get("username") == GITLAB_ACCOUNT_USERNAME :
                trigger_token_already_created = True
                trigger_token = token_info.get("token")
        
        if not trigger_token_already_created :
            print(f"Trigger token not created, Creating Trigger token of {project_name} project")
            response = request("post", url, headers, files=files, debug=debug)
            trigger_token = response.get("token")
            if debug :
                print(trigger_token)

    return trigger_token

def add_trigger_argument(project, type) :

    configuration_to_add = {}
    trigger_argument = TRIGGER_ARGUMENTS[type].split(',')

    for argument in trigger_argument :
        value = project.get(argument)
        if value != None :
            configuration_to_add[argument] = value
    
    return configuration_to_add

def create_ci_variables(token, all_setup, debug = False):
    headers = {"PRIVATE-TOKEN": token}
    files_trigger = {
        'description': (None, TRIGGER_DESCRIPTION),
    }
    all_project_configuration = {}

    for project_to_trigger in all_setup :
        trigger_token = config_trigger_token(project_to_trigger, headers, files_trigger, debug)
        projects_to_setup = project_to_trigger.get("projects")
        project_to_trigger_type = project_to_trigger.get("type")
        project_to_trigger_name = project_to_trigger.get("name")
        for project in projects_to_setup :
            project_configuration = {}
            variable = {}
            variable_name = "variable"
            project_name = project.get("name")
            project_id = project.get("id")
            
            project_configuration["name"] = project_name

            variable[project_to_trigger_name] = {}
            variable[project_to_trigger_name] = variable[project_to_trigger_name] | add_trigger_argument(project,"all")
            variable[project_to_trigger_name] = variable[project_to_trigger_name] | add_trigger_argument(project,project_to_trigger_type)
            variable[project_to_trigger_name]["type"] = project_to_trigger_type
            
            
            configuration_to_add = {}
            if project_to_trigger_type == "gitlab" :
                project_to_trigger_id = project_to_trigger.get("id")
                configuration_to_add["id"] = project_to_trigger_id
                configuration_to_add["token_name"] = f'{GITLAB_VARIABLE_TRIGGER_KEY}_{project_to_trigger_id}'
                configuration_to_add["token"] = trigger_token

                variable_name = GITLAB_VARIABLE_TRIGGER_CONFIGURATION_KEY
            if project_to_trigger_type == "jenkins" :
                token_name = variable[project_to_trigger_name].get("token_name")
                if token_name == None :
                    configuration_to_add["token_name"] = JENKINS_TRIGGER_TOKEN_NAME
                else :
                    configuration_to_add["token_name"] = token_name

                configuration_to_add["token"] = os.environ.get(configuration_to_add.get("token_name"),"")

                variable_name = JENKINS_VARIABLE_TRIGGER_CONFIGURATION_KEY

            variable[project_to_trigger_name] = variable[project_to_trigger_name] | configuration_to_add

            project_configuration[variable_name] = variable

            if project_id in all_project_configuration.keys() :
                if variable_name in all_project_configuration[project_id].keys() :
                    all_project_configuration[project_id][variable_name] = all_project_configuration[project_id][variable_name] | project_configuration[variable_name]
                else :
                    all_project_configuration[project_id][variable_name] = project_configuration[variable_name]
            else :
                all_project_configuration[project_id] = project_configuration

    return all_project_configuration

def set_new_ci_variable(headers, project_id, project_variables, variable_key, variable_value, variable_masked, debug = False) :
    variable_already_put = False

    for variable in project_variables :
        if variable.get("key") == variable_key :
            variable_already_put = True
    
    if variable_already_put :
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables/{variable_key}?value={variable_value}"
        request("put", url, headers, debug = debug)
    else :
        print(f"Setup {variable_key} for {project_id} project")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
        payload = {
            'key': variable_key,
            'value': variable_value,
            'masked': variable_masked,
        }
        request("post", url, headers, payload_data=payload, debug = debug)

    return variable_already_put

def set_ci_variables(token,all_project_configuration, debug = False):
    headers = {"PRIVATE-TOKEN": token}

    for project_id,project_configuration in all_project_configuration.items() :
        if project_id == 27032 :
            project_name = project_configuration.pop('name')

            url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
            print(f"Getting variables for {project_name} project")
            project_variables = request("get", url, headers, debug = debug)
            if debug :
                print(project_variables)

            for variable_name in project_configuration.keys() :
                for project_to_trigger_name,variable in project_configuration.get(variable_name).items() :
                    variable_already_put = set_new_ci_variable(headers, project_id, project_variables, variable.get("token_name"), variable.get("token"), True, debug)
                    variable.pop("token")
                    if not variable_already_put :
                        send_message(f"🔔 Le projet {project_name} a bien été configuré pour trigger le projet {project_to_trigger_name}. Pour plus d'information voir : {CI_JOB_URL}")
                
                set_new_ci_variable(headers, project_id, project_variables, variable_name, json.dumps(project_configuration.get(variable_name)), False, debug)


def set_allowlist(token, headers, project_allowlist, project_id, project_to_allow_id, debug = False) :
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope/allowlist"
    payload = {'target_project_id': project_to_allow_id}
    project_allowlist_already_setup = False

    for project in project_allowlist :
        if project.get("id") == project_to_allow_id :
            project_allowlist_already_setup = True

    if not project_allowlist_already_setup :
        request("post",url, headers, payload_data=payload, debug=debug)
    else : 
        print("Already added to allowlist.")

def set_project_allowlist(token, all_setup, debug = False):
    headers = {"PRIVATE-TOKEN": token}

    for project_to_trigger in all_setup :
        projects_to_setup = project_to_trigger.get("projects")
        project_to_trigger_type = project_to_trigger.get("type")
        project_to_trigger_name = project_to_trigger.get("name")
        project_to_trigger_dependencies = project_to_trigger.get("dependencies", [])
        if project_to_trigger_type == "gitlab" :
            project_to_trigger_id = project_to_trigger.get("id")
            for project in projects_to_setup :
                project_name = project.get("name")
                project_id = project.get("id")
                print(f"Setting allowlists of {project_name} project")

                if project_id == 27032 :
                    print(f"Enabling allowlists of {project_name} project...")
                    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope"
                    payload = {'enabled': True}
                    request("patch",url, headers, payload_data=payload, debug=debug)
                    
                    print(f"Getting allowlists of {project_name} project...")
                    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope/allowlist"
                    project_allowlist = request("get",url, headers, debug=debug)
                    if debug : 
                        print(project_allowlist)
                    
                    print(f"Adding to allowlists of {project_name} project, {project_to_trigger_name} project...")
                    set_allowlist(token, headers, project_allowlist, project_id, project_to_trigger_id, debug)

                    print(f"Adding {project_to_trigger_name} project dependencies to allowlists of {project_name} project...")
                    for dependencies in project_to_trigger_dependencies :
                        dependencies_id = dependencies.get("id")
                        set_allowlist(token, headers, project_allowlist, project_id, dependencies_id, debug)
                    
                    print(f"Getting allowlists of {project_to_trigger_name} project...")
                    url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/job_token_scope/groups_allowlist?per_page=100"
                    project_to_trigger_allowlist = request("get", url, headers, debug=debug)
                    if debug : 
                        print(project_to_trigger_allowlist)

                    project_to_trigger_allowlist_already_setup = False

                    url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
                    print(f"Getting {project_name} project info...")
                    project_info = request("get", url, headers, debug=debug)
                    if debug : 
                        print(project_info)

                    for project in project_to_trigger_allowlist :
                        if project.get("id") == project_info.get("namespace",{}).get("id") :
                            project_to_trigger_allowlist_already_setup = True
                    
                    if not project_to_trigger_allowlist_already_setup :
                        print(f"Adding {project_name} namespace to allowlists of {project_name} project...")
                        url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/job_token_scope/groups_allowlist"
                        payload = {'target_group_id': project_info.get("namespace",{}).get("id")}
                        request("post",url, headers, payload_data=payload, debug=debug)

def main(args) :
    all_setup = read_setup_files(args.folder_path)
    set_config_path(args.token,all_setup)
    all_project_configuration = create_ci_variables(args.token,all_setup)
    print(all_project_configuration)
    set_ci_variables(args.token, all_project_configuration)
    set_project_allowlist(args.token,all_setup)

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser and mutually exclusive group
parser = argparse.ArgumentParser(
    prog='CICD Python Helper',
    description="Programme permettant de gérer les logs/artifacts des projets gitlab")
# group = parser.add_mutually_exclusive_group(required=True)
parser.add_argument(
    '-d', '--debug-enabled', 
    metavar='DEBUG', default=False,
    help="Afficher plus de logs lors de l'éxécution des fonctions")
parser.add_argument(
    '-fp', '--folder-path', 
    metavar='FOLDER_PATH', default='trigger-project/setup/',
    help="Afficher plus de logs lors de l'éxécution des fonctions")
parser.add_argument(
    '-tok', '--token', 
    metavar='TOKEN', default='',
    help="Token pour accéder à gitlab")

# Run the arguments parser
args = parser.parse_args()

if args.debug_enabled == 'false' :
    args.debug_enabled = False
elif args.debug_enabled == 'true' :
    args.debug_enabled = True

if(args.debug_enabled):
    print(args)

main(args)

# End
print("\r")