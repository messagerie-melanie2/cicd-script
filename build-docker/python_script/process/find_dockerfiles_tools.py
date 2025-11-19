# coding=utf-8
from global_vars import *
from process.class_pipeline import InfoFromPath, InfoFromDockerfile, Deploy, Parameters, MultiStageParent
from gitlab.gitlab_tools import get_repository_id

#=======================================================#
#========= Find Dockerfiles Tools Functions ============#
#=======================================================#

##### Tools functions

def find_arg(content, name, debug = False):

    # Get all the lines containing a 'ARG $name' instruction
    matches = re.findall("^ARG " + name + ".*$", content, re.MULTILINE)

    if(debug):
        print("Matches : ")
        print(matches)

    # No need to check for a # (comment), the regex does it

    # If we have at least a match
    if(len(matches) > 0):

        # Keep the first occurence only
        match = matches[0]

        # Remove the 'ARG $name=' part of the instruction
        match = re.sub(r"ARG " + re.escape(name) + r"=(.*)", r'\1', match)

        if(len(match) > 0):
            if(debug):
                print("Result : " + match)

            if(match == 'true'):
                return {'success': True, 'match': True}

            if(match == 'false'):
                return {'success': True, 'match': False}

            return {'success': True, 'match': match}
        else:
            if(debug):
                print("Dockerfile's 'ARG " + name + "' seem to be empty...")
    
    else:
        if(debug):
            print("Dockerfile without 'ARG " + name + "'...")

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

def process_from_line(df_from, debug = False):
    # Remove the 'FROM ' part of the string
    df_from_without_from = re.sub('FROM (.*)', r'\1', df_from)
    if(debug):
        print("processing... : " + df_from_without_from)

    # Remove default value placeholders
    # like ':-${registry_default}' in '${registry:-${registry_default}}'
    # like '${parent_version_default}' in '${parent_version:-${parent_version_default}}'
    df_from_without_placeholder = re.sub(":-\${[a-zA-Z0-9_-]*}", '', df_from_without_from)
    if(debug):
        print("processing... : " + df_from_without_placeholder)
        
    # Remove variable placeholders
    # like '${registry}' in '${registry:-${registry_default}}'
    # like '${parent_version}' in '${parent_version:-${parent_version_default}}'
    df_from_without_placeholder = re.sub("\${[a-zA-Z0-9_-]*}", '', df_from_without_placeholder)
    if(debug):
        print("processing... : " + df_from_without_placeholder)

    # Remove version substring (after ':' like ':version')
    df_from_without_version = re.sub("(.*):[a-zA-Z0-9_.-]*", r'\1', df_from_without_placeholder)
    if(debug):
        print("processing... : " + df_from_without_version)
    
    # Remove AS alias if multistage
    df_from_without_alias = re.sub("(.*) AS [a-zA-Z0-9_.-]*", r'\1', df_from_without_version)
    if(debug):
        print("processing... : " + df_from_without_alias)

    # Remove leading slash
    image_name = re.sub("/*([a-zA-Z0-9_/-]*)", r'\1', df_from_without_alias)
    if(debug):
        print("processing... : " + image_name)
    
    return image_name

def find_parent_name(content, current_repo, debug = False):
        
    # Get the lines containing a 'FROM' instruction
    df_froms = re.findall("^FROM.*$", content, re.MULTILINE)

    if(len(df_froms) > 0):

        # Store the last line with a 'FROM' instruction
        df_from = df_froms[len(df_froms)-1]
        if(debug):
            print("processing... : " + df_from)

        # Determine if parent is external or not (current repo or not)
        external = find_if_external(content,current_repo,df_from)

        image_name = process_from_line(df_from,debug)

        return [image_name, external]

    else:
        # if(debug):
        print("Dockerfile without FROM...")
        return False

def find_multistage_parents(content, current_repo, debug = False):
        
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
        multistage_parent["name"] = process_from_line(from_line,debug)

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

    if (debug) :
        print("Multistage parents : ")
        print(multistage_parents)
    
    return multistage_parents

##### Find functions

def find_info_from_path(path, debug = False):
    '''
    Extract information from the path himself
    '''

    reg_result = re.search('(?:\./){0,1}((.*/)?([a-zA-Z0-9_-]*)/([0-9]+.[0-9]+))/Dockerfile', path)

    if(reg_result == None or len(reg_result.groups()) < InfoFromPath.count):

        if(debug):
            print("No info could be found (or not enough), check your path...")

        return None

    else:

        if(debug):
            print(reg_result.groups())

        return InfoFromPath(reg_result)

def find_info_from_dockerfile(current_repo, path = DOCKER_FILE_NAME, debug = False):
    '''
    Extract information from the Dockerfile
    '''

    try:
        # Read Dockerfile
        df_file = open(path, 'r')

    except OSError as err:
        print("{0} not found... ({1})".format(DOCKER_FILE_NAME, err))
        return None

    else:
        # Store Dockerfile content
        df_content = df_file.read()
        df_file.close()

        # Extract args
        args = [
            find_arg(df_content, "parent_version_default", debug)["match"], # String
            find_arg(df_content, "parent_version_replace_with", debug)["match"], # False, or replacement
            # find_arg(df_content, "image_version_default", debug), # String
            find_arg(df_content, "image_version_replace", debug)["match"], # Boolean
        ]

        # Add parent info
        args += find_parent_name(df_content, current_repo, debug) # [String, Boolean]

        # Add dependencies info
        
        args.append(find_multistage_parents(df_content, current_repo, debug))

        if(args == None or len(args) < InfoFromDockerfile.count ):

            if(debug):
                print("No info could be found (or not enough), check your Dockerfile...")

            return None

        else:

            if(debug):
                print(args)

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

def find_info_from_parameters(subdir, default_version, debug = False):

    parametersInfo = []

    try:
        with open(subdir + os.sep + PARAMETERS_FILE_NAME, 'r') as parameters_file:
            try:
                parameters = yaml.safe_load(parameters_file)
            except yaml.YAMLError as exc:
                if debug :
                    print("{0} file not found... Will use default parent version.".format(PARAMETERS_FILE_NAME))
                    print(exc)
            else:
                no_build = parameters['no_build']
                no_repo = parameters['no_repo']

                try :
                    deploy_jenkins= parameters['deploy_jenkins']         
                except Exception as e:
                    if debug :
                        print("deploy_jenkins not in parameters.yml")
                    deploy_jenkins= PROD_KEY

                try :
                    no_deploy= parameters['no_deploy'] 
                    for i in range(len(no_deploy)) :
                        no_deploy[i] = Deploy[no_deploy[i]]           
                except Exception as e:
                    if debug :
                        print("no_deploy not in parameters.yml")
                    no_deploy= [Deploy.NONE]

                try :
                    variables = parameters['variables']        
                except Exception as e:
                    if debug :
                        print("variables not in parameters.yml")
                    variables= None
                
                try :
                    multistage_parents = parameters['multistage_parents']        
                except Exception as e:
                    if debug :
                        print("multistage not in parameters.yml")
                    multistage_parents= None
                else :
                    for index,stage_info in enumerate(multistage_parents) :
                        stage_info_with_fullname = set_fullname_parent_version(stage_info)
                        multistage_parents[index] = stage_info_with_fullname

                for parent_version in parameters['parent_version']:
                    parent_version = set_fullname_parent_version(parent_version)        
                    parametersInfo.append(Parameters(True,parent_version,no_build,no_repo,no_deploy,deploy_jenkins,variables,multistage_parents))

    except Exception as e:
        if debug :
            print("{0} file not found... Will use default parent version.".format(PARAMETERS_FILE_NAME))
            print(e)
        
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

def find_info_from_changesfile(changes, df_name, df_version_number = "None", df_external = False, debug = False):

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
        
        if debug :
            print("{0} is {1}changed in the commit".format(df_name,"" if is_changed else "not ") )

    return is_changed

def check_if_triggered(stage_parent,triggered_project,trigger_changes):
    is_triggered = False

    if triggered_project in stage_parent.project_dependency :
        print(stage_parent.project_dependency)
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

def convert_variables_to_kaniko_arg(variables, branch, debug):

    kaniko_args=""
    if variables != None :
        for variable in variables:
            name = variable["name"]
            
            if variable["default"] == None :
                print("no default field in {0} variable fields. It will be skipped.".format(name))
            else:
                value = variable["default"]

                if branch == PROD_KEY or branch == PREPROD_KEY :
                    try :
                        value = variable[branch]       
                    except Exception as e:
                        if debug :
                            print("no {0} field in {1} variable fields.".format(branch,name))
                else :
                    try :
                        value = variable["dev"]       
                    except Exception as e:
                        if debug :
                            print("no dev field in {0} variable fields.".format(name))
                
                try :
                    if variable["type"] == "env":
                        var_env = os.environ.get(value)
                        value = var_env
                except Exception as e:
                    if debug :
                        print("no env type in {0} variable fields.".format(name))
                
                kaniko_args += "--build-arg {0}={1} ".format(name,value)
        
    if debug:
        print("kaniko_args : " + kaniko_args)

    return kaniko_args

def no_build_file_in_folder(subdir,debug = False):
    is_in_folder = False

    try:
        # Try to find/read the NO_BUILD file
        df_file = open(subdir + os.sep + NOBUILD_FILE_NAME, 'r')
    except OSError as err:
        if(debug):
            print("No {0} file found, taking that image/version.".format(NOBUILD_FILE_NAME))
    else:
        # Add this to the list of images to NOT build
        is_in_folder = True
        if(debug):
            print("{0} file found, skipping that image/version.".format(NOBUILD_FILE_NAME))

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