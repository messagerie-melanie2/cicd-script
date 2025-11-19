# coding=utf-8
import argparse
import requests
import subprocess
import sys
import os
import json
import fnmatch
import yaml

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
GITLAB_REPO = "https://gitlab-forge.din.developpement-durable.gouv.fr"
JENKINS_URL = {"prod":"https://jenkins-prod.mel.edcs.fr/jenkins-prod/generic-webhook-trigger/invoke","preprod":"https://jenkins-preprod.mel.edcs.fr/jenkins-preprod/generic-webhook-trigger/invoke"}
TRIGGER_PARAMETERS_FILE_NAME = "./trigger_parameters.yml"
DESCRIPTION_VARIABLES = [{'tag': "--parent-recette",'name':"CI_PARENT_RECETTE"}]

#=======================================================#
#======================== Main =========================#
#=======================================================#

def get_changes(commit_before_sha, commit_sha, debug):
    changes = ""
    #Launch a git diff
    try :
        changes = subprocess.check_output(['git','diff','--name-only',commit_before_sha,commit_sha]).decode(sys.stdout.encoding)
        changes = ' '.join(changes.splitlines())

    except subprocess.CalledProcessError as err:
        print("Git diff failed...({0})".format(err))
        return(changes)
    else :
        if debug :
            print(changes)
        return(changes)

def read_trigger_parameters(config, debug):
    config_with_parameters = config.copy()
    try:
        with open(TRIGGER_PARAMETERS_FILE_NAME, 'r') as trigger_parameters:
            try:
                parameters = yaml.safe_load(trigger_parameters)
            except yaml.YAMLError as exc:
                if debug :
                    print("{0} file cannot be load.".format(TRIGGER_PARAMETERS_FILE_NAME))
                    print(exc)
            else:
                for project in parameters :
                    try :
                        project_config = config_with_parameters[project["name"]]
                    except Exception as e:
                            if debug :
                                print("{0} not in trigger_parameters.yml".format(project['name']))
                    else:

                        try :
                            trigger_files = project['trigger_files']   
                        except Exception as e:
                            if debug :
                                print("trigger_files of {0} not in trigger_parameters.yml".format(project['name']))
                            trigger_files = None
                        else:
                            config_with_parameters[str(project["name"])]["trigger_files"] = trigger_files
                        
                        try :
                            focus_trigger = project['focus_trigger']   
                        except Exception as e:
                            if debug :
                                print("focus_trigger of {0} not in trigger_parameters.yml".format(project['name']))
                            focus_trigger = None
                        else:
                            config_with_parameters[str(project["name"])]["focus_trigger"] = focus_trigger
                        
                        try :
                            branchs_only_trigger = project['branchs_only_trigger']   
                        except Exception as e:
                            if debug :
                                print("branchs_only_trigger of {0} not in trigger_parameters.yml".format(project['name']))
                            branchs_only_trigger = None
                        else:
                            config_with_parameters[str(project["name"])]["branchs_only_trigger"] = branchs_only_trigger
                        
                        try :
                            branchs_mapping = project['branchs_mapping'] 
                        except Exception as e:
                            if debug :
                                print("branchs_mapping of {0} not in trigger_parameters.yml".format(project['name']))
                            branchs_mapping = None
                        else:
                            config_with_parameters[str(project["name"])]["branchs_mapping"] = branchs_mapping

    except Exception as e:
        if debug :
            print("{0} file not found...".format(TRIGGER_PARAMETERS_FILE_NAME))
            print(e)
    
    return config_with_parameters

def trigger_gitlab(project_to_trigger,project_to_trigger_config, project, branch, description, changes, token, debug):
    trigger = False

    try :
        trigger_files = project_to_trigger_config["trigger_files"]         
    except Exception as e:
        trigger = True
    else:
        changes_list = changes.split(" ")
        for change in changes_list :
            for file in trigger_files :
                if fnmatch.fnmatch(change,'*' + file + '*') :
                    trigger = True
    
    if trigger :
        trigger_token = os.getenv(project_to_trigger_config["trigger_token_name"])
        
        try :
            branchs_mapping = project_to_trigger_config["branchs_mapping"]         
        except Exception as e:
            if debug :
                print("branchs_mapping not in config")
            mapping = branch
        else:
            try :
                mapping = branchs_mapping[branch]         
            except Exception as e:
                if debug :
                    print("branch {0} not in branchs_mapping".format(branch))
                mapping = branch
        
        variables_json = {}
        for variable in DESCRIPTION_VARIABLES :
            if variable["tag"] in description :
                variables_json[variable["name"]] = True

        files = {
            'token': (None, trigger_token),
            'ref': (None, mapping),
            'variables[CI_PROJECT_TRIGGER]': (None, project),
            'variables[CI_BRANCH_TRIGGER]': (None, branch),
            'variables[TRIGGER_DESCRIPTION]': (None, description),
            'variables[TRIGGER_VARIABLES]' : (None, f"{variables_json}"),
        }

        try :
            focus_trigger = project_to_trigger_config["focus_trigger"]         
        except Exception as e:
            if debug :
                print("focus_trigger not in config")
        else:
            if focus_trigger :
                files["variables[CI_CHANGES_TRIGGER]"] = (None, changes)

        url = GITLAB_REPO + '/api/v4/projects/' + str(project_to_trigger_config["id"])   + '/trigger/pipeline'

        response = requests.post(
            url,
            files=files,
            auth=('gitlab-ci-token', token),
        )

        response.raise_for_status()

        try:
            data = response.json()
        except requests.JSONDecodeError:
            data = response

        if debug :
            print("Response gitlab project n°{0} : {1}".format(project_to_trigger_config["id"],data))
        
        print("Trigger success \n")

    else :
        print("{0} changes is not in trigger_files : {1} for project {2}, trigger will not be launched".format(changes,project_to_trigger_config["trigger_files"],project_to_trigger))

def trigger_jenkins(project_to_trigger, project_to_trigger_config, branch, changes, debug):
    trigger = False

    try :
        trigger_files = project_to_trigger_config["trigger_files"]         
    except Exception as e:
        trigger = True
    else:
        changes_list = changes.split(" ")
        for change in changes_list :
            for file in trigger_files :
                if fnmatch.fnmatch(change,'*' + file + '*') :
                    trigger = True
    
    if trigger :

        trigger_token = os.getenv("JENKINS_TRIGGER_TOKEN")

        try :
            branchs_mapping = project_to_trigger_config["branchs_mapping"]         
        except Exception as e:
            if debug :
                print("branchs_mapping not in config")
            mapping = branch
        else:
            try :
                mapping = branchs_mapping[branch]         
            except Exception as e:
                if debug :
                    print("branch {0} not in branchs_mapping".format(branch))
                mapping = branch

        headers = {"token": trigger_token}

        try :
            url = JENKINS_URL[mapping]       
        except Exception as e:
            if debug :
                print("branch {0} not in JENKINS_URL".format(mapping))
            url = JENKINS_URL["prod"]
        
        try :
            additional_params = project_to_trigger_config["additional_params"]       
        except Exception as e:
            if debug :
                print("additional_params not in config")
            additional_params = None
        

        data = {"pipeline_name":project_to_trigger}

        if additional_params != None :
            data["additional_params"] = additional_params

        response = requests.post(url=url,headers=headers,json=data)

        try:
            data = response.json()
        except requests.JSONDecodeError:
            data = response

        if debug :
            print("Response jenkins pipeline : {1}".format(project_to_trigger,data))
        
        print("Trigger success \n")

    else :
        print("{0} changes is not in trigger_files : {1} for project {2}, trigger will not be launched".format(changes,project_to_trigger_config["trigger_files"],project_to_trigger))

def trigger(config, project, branch, description, changes, token, debug):
    for key,value in config.items() :
        branch_trigger = False
        try :
            branchs_only_trigger = value["branchs_only_trigger"]         
        except Exception as e:
            branch_trigger = True
        else:
            if branch in branchs_only_trigger :
                branch_trigger = True

        if branch_trigger :
            project_type = value["type"]
            print("Launch triggering process of {0} project".format(key))
            if project_type == "gitlab" :
                trigger_gitlab(key, value, project, branch, description, changes, token, debug)
            elif project_type == "jenkins" :
                trigger_jenkins(key, value, branch, changes, debug)

        else :
            print("{0} branch is not in branchs_only_trigger : {1} for project {2}, trigger will not be launched".format(branch,value["branchs_only_trigger"],key))

def main(args):
    #Leave proxy
    os.environ["http_proxy"]=""
    os.environ["HTTP_PROXY"]=""
    os.environ["https_proxy"]=""
    os.environ["HTTPS_PROXY"]=""

    config = json.loads(args.config)
    config_with_parameters = read_trigger_parameters(config,args.debug_enabled)
    if args.debug_enabled : 
        print("config with parameters file : {0}".format(config_with_parameters))
    
    changes = get_changes(args.commit_before_sha,args.commit_sha,args.debug_enabled)
    trigger(config_with_parameters,args.project,args.branch,args.description,changes,args.token,args.debug_enabled)

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser
parser = argparse.ArgumentParser(
    prog='CICD Python Helper',
    description="Programme permettant de gérer les logs/artifacts des projets gitlab")

parser.add_argument(
    '-d', '--debug-enabled', 
    metavar='DEBUG', default=False,
    help="Afficher plus de logs lors de l'éxecution des fonctions")
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
parser.add_argument(
    '-c', '--config', 
    metavar='CONFIG', default=' ',
    help="configuration")

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