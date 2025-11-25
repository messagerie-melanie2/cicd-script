# coding=utf-8
import argparse
import requests
import os
import yaml
from datetime import datetime, timedelta

#=======================================================#
#================== Global parameters ==================#
#=======================================================#

GITLAB_URL = os.environ.get('GITLAB_PROTOCOL',"https://") + os.environ.get('GITLAB_DOMAIN',"")
GITLAB_CI_CONFIG_PATH = os.environ.get('GITLAB_CI_CONFIG_PATH',".gitlab-ci.yml@snum/detn/gmcd/cicd/cicd-yaml")
GITLAB_ACCOUNT_USERNAME = os.environ.get('GITLAB_ACCOUNT_USERNAME',"jenkins.inframel")
TRIGGER_DESCRIPTION = os.environ.get('TRIGGER_DESCRIPTION',"Trigger cree par Jenkins")

#=======================================================#
#======================== Main =========================#
#=======================================================#

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

def config_trigger_token(token, all_setup, debug = False):
    headers = {"PRIVATE-TOKEN": token}
    files = {
        'description': (None, TRIGGER_DESCRIPTION),
    }
    all_trigger_token = {}

    for project_to_trigger in all_setup :
        trigger_token = ""
        if project_to_trigger.get("type") == "gitlab" :
            print(f"Setting Trigger token of {project_to_trigger.get('name')} project")
            project_to_trigger_id = project_to_trigger.get("id")
            if project_to_trigger_id == 27032 :
                url = f"{GITLAB_URL}/api/v4/projects/{project_to_trigger_id}/triggers"
                try :
                    r = requests.get(url, headers=headers)
                    r.raise_for_status()
                except requests.exceptions.HTTPError as err:
                    if debug : 
                        print("Http Error:",err)
                    print(f"Setup failed : {r.json()}")
                else :
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
                            trigger_token = r.json.get("token")
                        
            all_trigger_token[project_to_trigger.get("name")] = trigger_token

def main(args) :
    all_setup = read_setup_files(args.folder_path)
    set_config_path(args.token,all_setup)
    config_trigger_token(args.token,all_setup)

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