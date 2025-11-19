# coding=utf-8
from global_vars import *

#=======================================================#
#============== Gitlab Tools Functions =================#
#=======================================================#

def get_registry_info(token, project_id = 0, debug = False):

    headers = {"PRIVATE-TOKEN": token}
    registry = []
    i = 0
    error = False

    #Max per page is only 100 so we have to loop to get all repositories
    while len(registry) == 100*i  and not error:
        url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/registry/repositories?per_page=100&page='+str(i+1)
        
        try :
            r = requests.get(url, headers=headers)
            r.raise_for_status()
        
        except requests.exceptions.HTTPError as err:
            if debug : 
                print("Http Error:",err)
            error = True
        
        else :
            registry += r.json()
            i += 1
    
    if debug :
        print(registry)
    
    return(registry)

def get_repository_id(registry,df_name,debug = False):
    
    repository_id = -1 

    for repository in registry :
        if repository["name"] == df_name :
            repository_id = repository["id"]
    
    if debug :
        print("{0} : {1}".format(df_name,repository_id))

    return repository_id

def get_tags_in_repository(token,project_id,repository_id, debug = False):
    tags = []
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/registry/repositories/'+str(repository_id)+'/tags?per_page=100'
    
    try :
        r = requests.get(url, headers=headers)
        r.raise_for_status()
    
    except requests.exceptions.HTTPError as err:
        if debug : 
            print("Http Error:",err)
        
    else :
        tags = r.json()
    
    return tags

def find_tag_in_repository(token,project_id,repository_id,tag_target, debug = False):

    tags = get_tags_in_repository(token,project_id,repository_id,debug)

    for tag in tags :
        if tag["name"] == tag_target :
            return True
    
    return False

def get_branches(token,project_id, debug = False):
    branches = []
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/repository/branches?per_page=100'
    
    try :
        r = requests.get(url, headers=headers)
        r.raise_for_status()
    
    except requests.exceptions.HTTPError as err:
        if debug : 
            print("Http Error:",err)
        
    else :
        branches = r.json()
    
    return branches

#DELETE

def delete_repository_in_registry(token,project_id,repository_id, debug = False):
    tags = []
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/registry/repositories/'+str(repository_id)
    deleted = False
    
    try :
        r = requests.delete(url, headers=headers)
        r.raise_for_status()
    
    except requests.exceptions.HTTPError as err:
        if debug : 
            print("Http Error:",err)
        
    else :
        deleted = True
    
    return deleted

def delete_tag_in_repository(token,project_id,repository_id,tag_name, debug = False):
    tags = []
    headers = {"PRIVATE-TOKEN": token}
    url = GITLAB_URL + 'api/v4/projects/'+str(project_id)+'/registry/repositories/'+str(repository_id)+'/tags/'+str(tag_name)
    deleted = False
    
    try :
        if debug :
            print("Url :" + url)
        r = requests.delete(url, headers=headers)
        r.raise_for_status()
    
    except requests.exceptions.HTTPError as err:
        if debug : 
            print("Http Error:",err)
        
    else :
        if debug :
            print("Request :",r.json())
        deleted = True
    
    return deleted