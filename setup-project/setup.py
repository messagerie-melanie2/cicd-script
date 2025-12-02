# coding=utf-8
import argparse
import requests
import os
import yaml
import json

#=======================================================#
#================== Global parameters ==================#
#=======================================================#

GITLAB_URL = os.environ.get('GITLAB_PROTOCOL',"https://") + os.environ.get('GITLAB_DOMAIN',"")
TRIGGER_CHANNEL_URL = os.environ.get('TRIGGER_CHANNEL_URL',"https://tchap-bot.mel.e2.rie.gouv.fr/api/webhook/post/VaUQRGFvb5WhklqC6VYmXSlmLKXrcSTbRmoefdzkAbjvh4yXkOqMGZtSsgCsC50bjt0rSyBn1PqWByTirXOYmwhdJMTZfKxnBGUt")
GITLAB_CI_CONFIG_PATH = os.environ.get('GITLAB_CI_CONFIG_PATH',".gitlab-ci.yml@snum/detn/gmcd/cicd/cicd-yaml")
GITLAB_ACCOUNT_USERNAME = os.environ.get('GITLAB_ACCOUNT_USERNAME',"jenkins.inframel")
TRIGGER_DESCRIPTION = os.environ.get('TRIGGER_DESCRIPTION',"Trigger cree par Jenkins")
TRIGGER_ARGUMENTS = {'all': 'trigger_files,branchs_only_trigger,branchs_mapping', 'gitlab': 'focus_trigger', 'jenkins': 'additional_params,token_name'}
GITLAB_VARIABLE_TRIGGER_KEY = os.environ.get('GITLAB_VARIABLE_TRIGGER_KEY',"TRIGGER_TOKEN")
JENKINS_TRIGGER_TOKEN_NAME = os.environ.get('JENKINS_TRIGGER_TOKEN_NAME',"JENKINS_TRIGGER_TOKEN")
CI_JOB_URL = os.environ.get('CI_JOB_URL',"")
GITLAB_VARIABLE_TRIGGER_CONFIGURATION_KEY = os.environ.get('GITLAB_VARIABLE_TRIGGER_CONFIGURATION_KEY',"GITLAB_TRIGGER_CONFIGURATION")
JENKINS_VARIABLE_TRIGGER_CONFIGURATION_KEY = os.environ.get('JENKINS_VARIABLE_TRIGGER_CONFIGURATION_KEY',"JENKINS_TRIGGER_CONFIGURATION")

#=======================================================#
#======================== Main =========================#
#=======================================================#

def send_message(message, debug = False):
    if TRIGGER_CHANNEL_URL != "" :
        #headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            'message': message,
            'message_raw': message
        }
        try :
            r = requests.post(TRIGGER_CHANNEL_URL,json=payload)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if debug : 
                print("Http Error:",err)
            print(f"Setup failed : {r.json()}")

def read_setup_files(folder_path, debug = False):
    all_setup = []
    my_path = os.path.abspath(os.path.dirname(__file__))
    my_project_path = my_path.split("cicd-script")[0]
    setup_path = os.path.join(my_project_path, folder_path)
    for subdir, dirs, files in os.walk(setup_path):
        for filename in files:
            filepath = subdir + os.sep + filename
            print(filename)
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
            print(project_id)
            if project.get("change_ci") != False :
                if project_id == 27032 :
                    print(f"Setting ci config path of {project.get('name')} project")
                    url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
                    try :
                        r = requests.put(url, files=files, headers=headers)
                        r.raise_for_status()
                    except requests.exceptions.HTTPError as err:
                        if debug : 
                            print("Http Error:",err)
                        print(f"Setup failed : {r.json()}")

def config_trigger_token(project_to_trigger, headers, files, debug = False):
    trigger_token = ""
    if project_to_trigger.get("type") == "gitlab" :
        print(f"Setting Trigger token of {project_to_trigger.get('name')} project")
        project_to_trigger_id = project_to_trigger.get("id")
        url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/triggers"
        try :
            r = requests.get(url, headers=headers)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if debug : 
                print("Http Error:",err)
            print(f"Setup failed : {r.json()}")
        else :
            print(r.json())
            project_to_trigger_tokens = r.json()
            trigger_token_already_created = False

            for project_token in project_to_trigger_tokens :
                if project_token.get("owner").get("username") == GITLAB_ACCOUNT_USERNAME :
                    trigger_token_already_created = True
                    trigger_token = project_token.get("token")
            
            if not trigger_token_already_created :
                try :
                    r = requests.post(url, files=files, headers=headers)
                    r.raise_for_status()
                except requests.exceptions.HTTPError as err:
                    if debug : 
                        print("Http Error:",err)
                    print(f"Setup failed : {r.json()}")
                else :
                    trigger_token = r.json().get("token")

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

                project_configuration["variable_name"] = GITLAB_VARIABLE_TRIGGER_CONFIGURATION_KEY
            if project_to_trigger_type == "jenkins" :
                token_name = variable[project_to_trigger_name].get("token_name")
                if token_name == None :
                    configuration_to_add["token_name"] = JENKINS_TRIGGER_TOKEN_NAME
                else :
                    configuration_to_add["token_name"] = token_name

                configuration_to_add["token"] = os.environ.get(configuration_to_add.get("token_name"),"")

                project_configuration["variable_name"] = JENKINS_VARIABLE_TRIGGER_CONFIGURATION_KEY

            variable[project_to_trigger_name] = variable[project_to_trigger_name] | configuration_to_add

            project_configuration["variable"] = variable

            if project_id in all_project_configuration.keys() :
                all_project_configuration[project_id]["variable"] = all_project_configuration[project_id]["variable"] | project_configuration["variable"]
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
        try :
            r = requests.put(url, headers=headers)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if debug : 
                print("Http Error:",err)
            print(f"Setup failed : {r.json()}")
    else :
        print(f"Setup {variable_key} for {project_id} project")
        url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
        payload = {
            'key': variable_key,
            'value': variable_value,
            'masked': variable_masked,
        }
        print(payload)
        try :
            r = requests.post(url, data=payload, headers=headers)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if debug : 
                print("Http Error:",err)
            print(f"Setup failed : {r.json()}")

    return variable_already_put

def set_ci_variables(token,all_project_configuration, debug = False):
    headers = {"PRIVATE-TOKEN": token}

    for project_id,project_configuration in all_project_configuration.items() :
        if project_id == 27032 :
            url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
            try :
                r = requests.get(url, headers=headers)
                r.raise_for_status()
            except requests.exceptions.HTTPError as err:
                if debug : 
                    print("Http Error:",err)
                print(f"Setup failed : {r.json()}")
            else :
                project_variables = r.json()

            for project_to_trigger_name,variable in project_configuration.get("variable").items() :
                variable_already_put = set_new_ci_variable(headers, project_id, project_variables, variable.get("token_name"), variable.get("token"), True, debug)
                variable.pop("token")
                if not variable_already_put :
                    send_message(f"🔔 Le projet {project_configuration.get('name')} a bien été configuré pour trigger le projet {project_to_trigger_name}. Pour plus d'information voir : {CI_JOB_URL}")
                
            set_new_ci_variable(headers, project_id, project_variables, project_configuration.get("variable_name"), json.dumps(project_configuration.get("variable")), False, debug)


def set_allowlist(token, headers, project_allowlist, project_id, project_to_allow_id, debug = False) :
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope/allowlist"
    payload = {'target_project_id': project_to_allow_id}
    project_allowlist_already_setup = False

    for project in project_allowlist :
        if project.get("id") == project_to_allow_id :
            project_allowlist_already_setup = True

    if not project_allowlist_already_setup :
        print("Adding to allowlist...")
        try :
            r = requests.post(url, data=payload, headers=headers)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if debug : 
                print("Http Error:",err)
            print(f"Setup failed : {r.json()}")
    else : 
        print("Already added to allowlist.")

def set_project_allowlist(token, all_setup, debug = False):
    headers = {"PRIVATE-TOKEN": token}

    for project_to_trigger in all_setup :
        projects_to_setup = project_to_trigger.get("projects")
        project_to_trigger_type = project_to_trigger.get("type")
        project_to_trigger_dependencies = project_to_trigger.get("dependencies", [])
        if project_to_trigger_type == "gitlab" :
            project_to_trigger_id = project_to_trigger.get("id")
            for project in projects_to_setup :
                print(f"Setting allowlists of {project.get('name')} project")
                project_id = project.get("id")

                if project_id == 27032 :
                    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope"
                    payload = {'enabled': True}
                    try :
                        r = requests.patch(url, data=payload, headers=headers)
                        r.raise_for_status()
                    except requests.exceptions.HTTPError as err:
                        if debug : 
                            print("Http Error:",err)
                        print(f"Setup failed : {r.json()}")
                    
                    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/job_token_scope/allowlist"
                    try :
                        r = requests.get(url, headers=headers)
                        r.raise_for_status()
                    except requests.exceptions.HTTPError as err:
                        if debug : 
                            print("Http Error:",err)
                        print(f"Setup failed : {r.json()}")
                    else :
                        project_allowlist = r.json()
                        
                    set_allowlist(token, headers, project_allowlist, project_id, project_to_trigger_id, debug)

                    for dependencies in project_to_trigger_dependencies :
                        dependencies_id = dependencies.get("id")
                        set_allowlist(token, headers, project_allowlist, project_id, dependencies_id, debug)
                    
                    url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/job_token_scope/groups_allowlist?per_page=100"
                    try :
                        r = requests.get(url, headers=headers)
                        r.raise_for_status()
                    except requests.exceptions.HTTPError as err:
                        if debug : 
                            print("Http Error:",err)
                        print(f"Setup failed : {r.json()}")
                    else :
                        project_to_trigger_allowlist = r.json()

                    project_to_trigger_allowlist_already_setup = False

                    url = f"{GITLAB_URL}/api/v4/projects/{project_id}"
                    try :
                        r = requests.get(url, headers=headers)
                        r.raise_for_status()
                    except requests.exceptions.HTTPError as err:
                        if debug : 
                            print("Http Error:",err)
                        print(f"Setup failed : {r.json()}")
                    else :
                        project_info = r.json()
                    
                    for project in project_to_trigger_allowlist :
                        if project.get("id") == project_info.get("namespace",{}).get("id") :
                            project_to_trigger_allowlist_already_setup = True
                    
                    if not project_to_trigger_allowlist_already_setup :
                        url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/job_token_scope/groups_allowlist"
                        payload = {'target_group_id': project_info.get("namespace",{}).get("id")}
                        try :
                            r = requests.post(url, data=payload, headers=headers)
                            r.raise_for_status()
                        except requests.exceptions.HTTPError as err:
                            if debug : 
                                print("Http Error:",err)
                            print(f"Setup failed : {r.json()}")

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