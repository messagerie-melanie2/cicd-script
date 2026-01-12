# coding=utf-8
from global_vars import *
from dockerbuild.class_pipeline import InfoFromPath, InfoFromDockerfile, Deploy, Parameters, MultiStageParent
from lib.gitlab_helper import get_repository_id

logger = logging.getLogger(__name__)

#=======================================================#
#========= Find Dockerfiles Tools Functions ============#
#=======================================================#

##### Tools functions

def find_arg(content, name):

    # Get all the lines containing a 'ARG $name' instruction
    matches = re.findall("^ARG " + name + ".*$", content, re.MULTILINE)

    logger.debug("Matches : ")
    logger.debug(matches)

    # No need to check for a # (comment), the regex does it

    # If we have at least a match
    if(len(matches) > 0):

        # Keep the first occurence only
        match = matches[0]

        # Remove the 'ARG $name=' part of the instruction
        match = re.sub(r"ARG " + re.escape(name) + r"=(.*)", r'\1', match)

        if(len(match) > 0):
            logger.debug(f"Result : {match}")

            if(match == 'true'):
                return {'success': True, 'match': True}

            if(match == 'false'):
                return {'success': True, 'match': False}

            return {'success': True, 'match': match}
        else:
            logger.debug(f"Dockerfile's 'ARG {name}' seem to be empty...")
    
    else:
        logger.debug("Dockerfile without 'ARG {name}'...")

    return {'success': False, 'match': False}

def find_if_external(content, current_repo, df_from):
    # Determine if parent is external or not (current repo or not)
    external = True
    if('${registry' in df_from):
        registry_default_arg = find_arg(content, "registry_default")
        if registry_default_arg["success"] :
            if(current_repo in registry_default_arg["match"]):
                external = False
        else :
            external = False
    
    return external

def process_from_line(df_from):
    # Remove the 'FROM ' part of the string
    df_from_without_from = re.sub('FROM (.*)', r'\1', df_from)
    logger.debug(f"processing... : {df_from_without_from}")

    # Remove default value placeholders
    # like ':-${registry_default}' in '${registry:-${registry_default}}'
    # like '${parent_version_default}' in '${parent_version:-${parent_version_default}}'
    df_from_without_placeholder = re.sub(":-\${[a-zA-Z0-9_-]*}", '', df_from_without_from)
    logger.debug(f"processing... : {df_from_without_placeholder}")
        
    # Remove variable placeholders
    # like '${registry}' in '${registry:-${registry_default}}'
    # like '${parent_version}' in '${parent_version:-${parent_version_default}}'
    df_from_without_placeholder = re.sub("\${[a-zA-Z0-9_-]*}", '', df_from_without_placeholder)
    logger.debug(f"processing... : {df_from_without_placeholder}")

    # Remove version substring (after ':' like ':version')
    df_from_without_version = re.sub("(.*):[a-zA-Z0-9_.-]*", r'\1', df_from_without_placeholder)
    logger.debug(f"processing... : {df_from_without_version}")
    
    # Remove AS alias if multistage
    df_from_without_alias = re.sub("(.*) AS [a-zA-Z0-9_.-]*", r'\1', df_from_without_version)
    logger.debug(f"processing... : {df_from_without_alias}")

    # Remove leading slash
    image_name = re.sub("/*([a-zA-Z0-9_/-]*)", r'\1', df_from_without_alias)
    logger.debug(f"processing... : {image_name}")
    
    return image_name

def find_parent_name(content, current_repo):
        
    # Get the lines containing a 'FROM' instruction
    df_froms = re.findall("^FROM.*$", content, re.MULTILINE)

    if(len(df_froms) > 0):

        # Store the last line with a 'FROM' instruction
        df_from = df_froms[len(df_froms)-1]
        logger.debug("processing... : " + df_from)

        # Determine if parent is external or not (current repo or not)
        external = find_if_external(content,current_repo,df_from)

        image_name = process_from_line(df_from)

        return [image_name, external]

    else:
        logger.warning("Dockerfile without FROM...")
        return False

def find_multistage_parents(content, current_repo):
        
    multistage_parents = []
    
    #Get all content from stages from a multistage docker
    stages_content = re.findall("(FROM [\s\S]+?AS\s+\w+[\s\S]+?(?=FROM|\Z))", content,re.MULTILINE)


    for stage in stages_content :
        # if debug : 
        #     print('--------- STAGE --------')
        #     print(stage)
        multistage_parent = {}
        #Get From line
        from_line = re.search("(FROM.*?)\n{1}",stage)
        from_line = from_line.group(1)

        #Get the docker name from this stage
        multistage_parent["name"] = process_from_line(from_line)

        multistage_alias = re.search("FROM .* AS (.*)",from_line)
        multistage_parent["alias"] = multistage_alias.group(1)

        multistage_version = ""
        if('${stage_' not in from_line):
            multistage_version = re.search("FROM .*:(.*) AS .*",from_line)
            multistage_version = multistage_version.group(1)
        
        multistage_parent["version"] = multistage_version

        multistage_parent["external"] = find_if_external(content,current_repo,from_line)

        multistage_parent["project_dependency"] = ""
        multistage_parent["files_dependency"] = ""

        if multistage_parent["name"] is not None and "git-mce-generic" in multistage_parent["name"]:
            #Look for the git project
            regex = GITLAB_URL.split('/')[2].replace(".","\.") + '(.*?)\.git'
            dependency = re.search(regex,stage)

            if dependency is not None :
                multistage_parent["project_dependency"] = dependency.group(1)
                regex = 'COPY .*?--from=' + multistage_parent["alias"] + ' .*?\/source\/(.*?) '
                files_dependency = re.findall(regex, content,re.MULTILINE)
                multistage_parent["files_dependency"] = files_dependency
        
        multistage_parents.append(multistage_parent)

    logger.debug("Multistage parents : ")
    logger.debug(multistage_parents)
    
    return multistage_parents

##### Find functions

def find_info_from_path(path):
    '''
    Extract information from the path himself
    '''

    reg_result = re.search('(?:\./){0,1}((.*/)?([a-zA-Z0-9_-]*)/([0-9]+.[0-9]+))/Dockerfile', path)

    if(reg_result == None or len(reg_result.groups()) < InfoFromPath.count):
        logger.debug("No info could be found (or not enough), check your path...")

        return None

    else:
        logger.debug(reg_result.groups())
        return InfoFromPath(reg_result)

def find_info_from_dockerfile(current_repo, path = DOCKER_FILE_NAME):
    '''
    Extract information from the Dockerfile
    '''

    try:
        # Read Dockerfile
        df_file = open(path, 'r')

    except OSError as err:
        logger.info(f"{DOCKER_FILE_NAME} not found... ({err})")
        return None

    else:
        # Store Dockerfile content
        df_content = df_file.read()
        df_file.close()

        # Extract args
        args = [
            find_arg(df_content, "parent_version_default")["match"], # String
            find_arg(df_content, "parent_version_replace_with")["match"], # False, or replacement
            # find_arg(df_content, "image_version_default"), # String
            find_arg(df_content, "image_version_replace")["match"], # Boolean
        ]

        # Add parent info
        args += find_parent_name(df_content, current_repo) # [String, Boolean]

        # Add dependencies info
        
        args.append(find_multistage_parents(df_content, current_repo))

        if(args == None or len(args) < InfoFromDockerfile.count ):
            logger.debug("No info could be found (or not enough), check your Dockerfile...")
            return None

        else:
            logger.debug(args)
            return InfoFromDockerfile(args)

def set_fullname_parent_version(parent_version):
    new_parent_version = parent_version.copy()

    new_parent_version['version_name'] = str(new_parent_version['version_name'])

    if(new_parent_version['version_number'] == None):
        new_parent_version['fullname'] = new_parent_version['version_name']
    else :
        new_parent_version['version_number'] = str(new_parent_version['version_number'])
        new_parent_version['fullname'] = new_parent_version['version_name'] + "_" + new_parent_version['version_number']
    
    return new_parent_version

def find_info_from_parameters(subdir, default_version):

    parametersInfo = []

    try:
        with open(subdir + os.sep + PARAMETERS_FILE_NAME, 'r') as parameters_file:
            try:
                parameters = yaml.safe_load(parameters_file)
            except yaml.YAMLError as exc:
                logger.debug(f"{PARAMETERS_FILE_NAME} file not found... Will use default parent version.")
                logger.debug(exc)
            else:
                no_build = parameters['no_build']
                no_repo = parameters['no_repo']

                try :
                    deploy_jenkins= parameters['deploy_jenkins']         
                except Exception as e:
                    logger.debug("deploy_jenkins not in parameters.yml")
                    deploy_jenkins= PROD_KEY

                try :
                    no_deploy= parameters['no_deploy'] 
                    for i in range(len(no_deploy)) :
                        no_deploy[i] = Deploy[no_deploy[i]]           
                except Exception as e:
                    logger.debug("no_deploy not in parameters.yml")
                    no_deploy= [Deploy.NONE]

                try :
                    variables = parameters['variables']        
                except Exception as e:
                    logger.debug("variables not in parameters.yml")
                    variables= None
                
                try :
                    multistage_parents = parameters['multistage_parents']        
                except Exception as e:
                    logger.debug("multistage not in parameters.yml")
                    multistage_parents= None
                else :
                    for index,stage_info in enumerate(multistage_parents) :
                        stage_info_with_fullname = set_fullname_parent_version(stage_info)
                        multistage_parents[index] = stage_info_with_fullname

                for parent_version in parameters['parent_version']:
                    parent_version = set_fullname_parent_version(parent_version)        
                    parametersInfo.append(Parameters(True,parent_version,no_build,no_repo,no_deploy,deploy_jenkins,variables,multistage_parents))

    except Exception as e:
        logger.debug(f"{PARAMETERS_FILE_NAME} file not found... Will use default parent version.")
        logger.debug(e)
        
    if len(parametersInfo) == 0 :
        if len(default_version.split("_")) == 1 :
            version_name=default_version
            version_number=""
        else :
            version_name=default_version.split("_")[0]
            version_number=default_version.split("_")[1]

        parametersInfo.append(Parameters(True,{'version_name':version_name,'version_number':version_number,'fullname':default_version},False,False,[Deploy.NONE], PROD_KEY, None))

    # return all values found
    return parametersInfo

def find_info_from_changesfile(changes, df_name, df_version_number = "None", df_external = False):

    is_changed = False
    changes_with_df = []

    #If dockerfile is external, don't look for changes
    if df_external == False :
        for change in changes :
            if df_name in change :
                #All changes with dockerfile name in it
                if (change[change.rfind(df_name) - 1] == "/" or change.rfind(df_name) - 1 < 0) and change[change.rfind(df_name) + len(df_name)] == "/":
                    changes_with_df.append(change)

        for change in changes_with_df :
            #If change is on the same version number
            if df_version_number in change and ".md" not in change.lower():
                is_changed = True
        
        logger.debug(f"{df_name} is {'' if is_changed else 'not '}changed in the commit" )

    return is_changed

def check_if_triggered(stage_parent,triggered_project,trigger_changes):
    is_triggered = False

    if triggered_project in stage_parent.project_dependency :
        logger.debug(stage_parent.project_dependency)
        #Check for focus trigger only if we have trigger changes
        if trigger_changes != "" :
            for file_dependency in stage_parent.files_dependency :
                trigger_changes_list = trigger_changes.split(" ")
                for trigger_change in trigger_changes_list :
                    trigger_change = triggered_project.split("/")[-1] + "/" + trigger_change
                    if fnmatch.fnmatch(trigger_change,'*' + file_dependency + '*') :
                        is_triggered = True
        else :
            is_triggered = True
    
    return is_triggered

def convert_variables_to_docker_args(variables, branch):

    docker_args=""
    if variables != None :
        for variable in variables:
            name = variable["name"]
            
            if variable["default"] == None :
                logger.info(f"no default field in {name} variable fields. It will be skipped.")
            else:
                value = variable["default"]

                if branch == PROD_KEY or branch == PREPROD_KEY :
                    try :
                        value = variable[branch]       
                    except Exception as e:
                        logger.debug(f"no {branch} field in {name} variable fields.")
                else :
                    try :
                        value = variable["dev"]       
                    except Exception as e:
                        logger.debug(f"no dev field in {name} variable fields.")
                
                try :
                    if variable["type"] == "env":
                        var_env = os.environ.get(value)
                        value = var_env
                except Exception as e:
                    logger.debug(f"no env type in {name} variable fields.")
                
                docker_args += f"{DOCKER_BUILD_ARG_OPTION}{name}={value} "
        
    logger.debug("docker_args : " + docker_args)

    return docker_args

def no_build_file_in_folder(subdir):
    is_in_folder = False

    try:
        # Try to find/read the NO_BUILD file
        df_file = open(subdir + os.sep + NOBUILD_FILE_NAME, 'r')
    except OSError as err:
        logger.debug(f"No {NOBUILD_FILE_NAME} file found, taking that image/version.")
    else:
        # Add this to the list of images to NOT build
        is_in_folder = True
        logger.debug("{NOBUILD_FILE_NAME} file found, skipping that image/version.")

    return is_in_folder

def create_multistage_parents(multistage_parents_info, registry, multistage_parents_parameters):
    multistage_parents = []
    
    for stage in multistage_parents_info :
        version = stage["version"]
        alias = stage["alias"]
        have_parameters = False

        if multistage_parents_parameters is not None :
            for stage_parameters in multistage_parents_parameters :
                if stage_parameters["alias"] == alias:
                    have_parameters = True
                    version = stage_parameters["fullname"]
        
        repository_id = get_repository_id(registry,stage["name"])

        multistage_parents.append(MultiStageParent(stage["name"],version,stage["external"],False,repository_id,alias,have_parameters,stage["project_dependency"],stage["files_dependency"]))
    
    return multistage_parents