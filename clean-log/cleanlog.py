# coding=utf-8
import argparse
import requests
import os
from datetime import datetime, timedelta
from environs import Env

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
env = Env()

GITLAB_URL = os.environ.get('GITLAB_PROTOCOL',"https://") + os.environ.get('GITLAB_DOMAIN',"")
STATUS_NO_LOG=env.list('STATUS_NO_LOG',["skipped","canceled"])

#=======================================================#
#============== Gitlab Tools Functions =================#
#=======================================================#

def get_jobs_info(token, project_id, weeks_limit, debug = False):

    headers = {"PRIVATE-TOKEN": token}
    jobs = []
    i = 0

    loop = True
    #Max per page is only 100 so we have to loop to get all repositories
    while loop and len(jobs) == 100*i:
        url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/jobs?per_page=100&page='+str(i+1)
        
        try :
            r = requests.get(url, headers=headers)
            r.raise_for_status()
        
        except requests.exceptions.HTTPError as err:
            if debug : 
                print("Http Error:",err)
            loop = False
        
        else :
            jobs += r.json()
            if weeks_limit != None :
                last_job = jobs[-1]
                if last_job["started_at"] != None :
                    last_job_date = datetime.strptime(last_job["started_at"][:-1], "%Y-%m-%dT%H:%M:%S.%f")
                    date_limit = datetime.now() - timedelta(weeks=weeks_limit*2)
                    if last_job_date < date_limit:
                        loop = False
            i += 1
    
    if debug :
        print(jobs)
    
    return(jobs)

def delete_job_artifacts(token,project_id, job, debug = False):
    tags = []
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/jobs/'+str(job["id"])+'/erase'
    deleted = False
    
    try :
        r = requests.post(url, headers=headers)
        r.raise_for_status()
    
    except requests.exceptions.HTTPError as err:
        if debug : 
            print("Http Error:",err)
        
    else :
        deleted = True
    
    return deleted

#=======================================================#
#======================== Main =========================#
#=======================================================#

def process_jobs(jobs, token, project_id, weeks_limit, debug = False):
    if weeks_limit != None :
        date_limit = datetime.now() - timedelta(weeks=weeks_limit)

    for job in jobs :
        if job["status"] not in STATUS_NO_LOG :
            if job["erased_at"] == None :
                if job["archived"] == False :
                    if weeks_limit != None and job["started_at"] != None:
                        job_date = datetime.strptime(job["started_at"][:-1], "%Y-%m-%dT%H:%M:%S.%f")
                        if job_date < date_limit:
                            deleted = delete_job_artifacts(token,project_id,job,debug)
                            if deleted :
                                print("job " + str(job["id"]) + " is erased")
                            else :
                                print("job " + str(job["id"]) + " couldn't be erased")
                    else :
                        deleted = delete_job_artifacts(token,project_id,job,debug)
                        if deleted :
                            print("job " + str(job["id"]) + " is erased")
                        else :
                            print("job " + str(job["id"]) + " couldn't be erased")
                else :
                    print("job " + str(job["id"]) + " is archived and can't be erased")
            else :
                print("job " + str(job["id"]) + " is already erased")
        

def main(args) :

    if(args.clean_job_rotation):
        jobs = get_jobs_info(args.token,args.project_id,int(args.weeks_limit),args.debug_enabled)
        process_jobs(jobs,args.token,args.project_id,int(args.weeks_limit),args.debug_enabled)

    if(args.clean_all):
        jobs = get_jobs_info(args.token,args.project_id,None,args.debug_enabled)
        process_jobs(jobs,args.token,args.project_id,None,args.debug_enabled)

#=======================================================#
#====================== Arguments ======================#
#=======================================================#

# Create arguments parser and mutually exclusive group
parser = argparse.ArgumentParser(
    prog='CICD Python Helper',
    description="Programme permettant de gérer les logs/artifacts des projets gitlab")
group = parser.add_mutually_exclusive_group(required=True)
parser.add_argument(
    '-d', '--debug-enabled', 
    metavar='DEBUG', default=False,
    help="Afficher plus de logs lors de l'éxécution des fonctions")
parser.add_argument(
    '-tok', '--token', 
    metavar='TOKEN', default='',
    help="Token pour accéder à gitlab")
parser.add_argument(
    '-pid', '--project-id', 
    metavar='PROJECT', default=0,
    help="Projet à traiter")

#####
# Argument to launch log rotation
#####
group.add_argument(
    '-cjr', '--clean-job-rotation', 
    action='store_true',
    help="Fais une rotation de log en effacant tous les jobs après la date limite")
parser.add_argument(
    '-wl', '--weeks-limit', 
    metavar='WEEKS_LIMIT', default=None,
    help="Limite de semaine autorisé")

#####
# Argument to clean all jobs
#####
group.add_argument(
    '-ca', '--clean-all',
    action='store_true',
    help="Lance l'effacement de toutes les jobs")

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