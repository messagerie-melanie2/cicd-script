from cleanlog.global_vars import *
from lib.helper import request

logger = logging.getLogger(__name__)

#=======================================================#
#================ Cleanlog Functions ===================#
#=======================================================#

def check_week_limit(jobs, weeks_limit):
    """
    Check if last job exceed 2 * weeks_limit in order to get enough jobs to delete or all job if weeks_limit is None.

    Args:
        jobs (list): List of jobs projects to process.
        weeks_limit (str): Week limit if double exceeded, stop the count.

    Returns:
        limit_not_exceeded (bool): Say if limit is exceeded or not.
    """
    limit_not_exceeded = True

    if weeks_limit != None :
        last_job = jobs[-1]
        if last_job["started_at"] != None :
            last_job_date = datetime.strptime(last_job["started_at"][:-1], "%Y-%m-%dT%H:%M:%S.%f")
            date_limit = datetime.now() - timedelta(weeks=int(weeks_limit)*2)
            if last_job_date < date_limit:
                limit_not_exceeded = False
    
    return limit_not_exceeded

def get_jobs_info(token, project_id, weeks_limit):
    """
    Get all project jobs info depending of weeks_limit parameters.

    Args:
        token (str): Token to use for authentication.
        project_id (int): Id of the project.
        weeks_limit (str): Week limit if double exceeded, stop the count.

    Returns:
        jobs (list): List of jobs projects to process.
    """
    headers = {"PRIVATE-TOKEN": token}
    jobs = []
    i = 0

    loop = True
    #Max per page is only 100 so we have to loop to get all repositories
    while loop and len(jobs) == 100*i:
        url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/jobs?per_page=100&page='+str(i+1)
        
        response = request("get", url=url, headers=headers)
        if response != {}:
            jobs += response
            loop = check_week_limit(jobs, weeks_limit)
        else :
            loop = False
        
        i += 1
    
    logging.debug(f"Jobs : {jobs}")
    
    return(jobs)

def delete_job_artifacts(token,project_id, job):
    """
    Erase job from gitlab.

    Args:
        token (str): Token to use for authentication.
        project_id (int): Id of the project.
        job (dict): Job to erase.

    Returns:
        deleted (bool): Say if the job is deleted or not.
    """
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/jobs/'+str(job["id"])+'/erase'
    deleted = False
    
    response = request("post", url=url, headers=headers)
    
    if response != {} :
        deleted = True
    
    return deleted

def process_jobs(jobs, token, project_id, weeks_limit):
    """
    Erase job from gitlab.

    Args:
        jobs (list): List of jobs projects to process.
        token (str): Token to use for authentication.
        project_id (int): Id of the project.
        weeks_limit (str): Week limit if exceeded, erase the job.
    """
    if weeks_limit != None :
        date_limit = datetime.now() - timedelta(weeks=int(weeks_limit))

    for job in jobs :
        if job["status"] not in CLEANLOG_STATUS_NO_LOG :
            if job["erased_at"] == None :
                if job["archived"] == False :
                    to_delete = True
                    if weeks_limit != None and job["started_at"] != None:
                        job_date = datetime.strptime(job["started_at"][:-1], "%Y-%m-%dT%H:%M:%S.%f")
                        if job_date >= date_limit:
                            to_delete = False

                    if to_delete :
                        deleted = delete_job_artifacts(token,project_id,job)
                        if deleted :
                            logging.info(f"job {job['id']} is erased")
                        else :
                            logging.info(f"job {job['id']} couldn't be erased")
                else :
                    logging.info(f"job {job['id']} is archived and can't be erased")
            else :
                logging.info(f"job {job['id']} is already erased")