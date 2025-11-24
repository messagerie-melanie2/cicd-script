# coding=utf-8
import argparse
import requests
import os
import yaml
from datetime import datetime, timedelta
from environs import Env

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
env = Env()

GITLAB_URL = os.environ.get('GITLAB_PROTOCOL',"https://") + os.environ.get('GITLAB_DOMAIN',"")
STATUS_NO_LOG=env.list('STATUS_NO_LOG',["skipped","canceled"])

#=======================================================#
#======================== Main =========================#
#=======================================================#

def read_setup_files(folder_path, debug = False):
    all_setup = []
    my_path = os.path.abspath(os.path.dirname(__file__))
    print(my_path)
    setup_path = os.path.join(my_path, folder_path)
    print(setup_path)
    for subdir, dirs, files in os.walk(setup_path):
        for filename in files:
            filepath = subdir + os.sep + filename
            print(filename)
            if filepath.endswith("triggers.yml"):
                with open(setup_path, 'r') as setup_file:
                    try:
                        setup_yaml = yaml.safe_load(setup_file)
                    except yaml.YAMLError as exc:
                        if debug :
                            print("Couldn't load yaml for {0} file...".format(setup_path))
                            print(exc)
                    else :
                        all_setup = all_setup + setup_yaml
    return all_setup

def set_config_path(token, all_setup, ci_config_path, debug = False):
    files = {
        'ci_config_path': (None, ci_config_path),
    }

    for project_to_trigger in all_setup :
        projects_to_setup = project_to_trigger.get("projects")
        for project in projects_to_setup :
            project_id = project.get("id")
            if project.get("change_ci") != False :
                url = f"{GITLAB_URL}/projects/{project_id}"
                response = requests.put(
                    url,
                    files=files,
                    auth=('gitlab-ci-token', token),
                )

def main(args) :
    all_setup = read_setup_files(args.folder_path)
    print(all_setup)
    #set_config_path(args.token,all_setup, args.ci_config_path)
    

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
    metavar='FOLDER_PATH', default='trigger-project/setup/triggers.yaml',
    help="Afficher plus de logs lors de l'éxécution des fonctions")
# parser.add_argument(
#     '-tok', '--token', 
#     metavar='TOKEN', default='',
#     help="Token pour accéder à gitlab")

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