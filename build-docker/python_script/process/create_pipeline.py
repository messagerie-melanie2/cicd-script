from global_vars import *
from process.class_pipeline import Deploy
from process.find_dockerfiles_tools import find_info_from_changesfile

#=======================================================#
#============= Create Pipeline Functions ===============#
#=======================================================#

def sort_dockerfiles(dockerfiles, debug = False):
    
    # Setup variables
    res = dockerfiles
    levels = DOCKER_IMAGES_PARENT_LEVELS
    sortedRes = [[] for _ in range(levels)]
    elementsToRemove = []
    roundCount = 1
    
    # Display debug information before doing the job
    if(debug):
        print("\n\rSorting following Dockerfiles, with a maximum of " + str(levels) + " levels...")
        for elem in res:
            print(elem)

    if(debug):
        print(">>> Searching for Dockerfiles with a parent outside this repo (DockerHub, other repo, ...)")
    #
    for df in dockerfiles:
        if df.parent.external == True:
        # if df.parent not in [dfi.name for dfi in dockerfiles]:
            if(debug):
                print("Found : " + str(df))
            sortedRes[0].append(df)
            elementsToRemove.append(df)

    # Update list to remove already-handled elements
    res = [e for e in res if e not in elementsToRemove]

    if(debug):
        print(">>> Searching for other (= child) Dockerfiles")
    #
    while (len(res) > 0 and roundCount < levels):

        if(debug):
            print("-- Loop level " + str(roundCount))

        # loop through Dockerfile element
        for elem in res:
            # loop through previous levels
            for level in range(roundCount):
                if (elem.parent.name, elem.parent.version) in {
                    (df.name, df.version) for df in sortedRes[level]
                }:
                    if(debug):
                        print("Found : " + str(elem))

                    sortedRes[level + 1].append(elem)
                    elementsToRemove.append(elem)
        
        # Increment counter
        roundCount += 1

        # Update list to remove already-handled elements
        res = [e for e in res if e not in elementsToRemove]

    if(len(res) > 0):
        print("[WARN] Unable to sort all Dockerfiles... Check their content (maybe a wrong or not existing parent is specified ?)")
        print("[INFO] Adding all these left Dockerfiles to the last level.")
        for elem in res:

            print("- " + str(elem))

            # Build that image without searching for its parent
            elem.parent.external = True
            if(debug):
                print("Modified : " + str(elem))

            # Add it to the last stage
            sortedRes[levels - 1].append(elem)
    
    # Return the array, only with non-empty levels
    sortedRes = [e for e in sortedRes if len(e) > 0]
    if(debug):
        print("\n\rNumber of levels : " + str(len(sortedRes)))
    return sortedRes

def set_parent_to_is_building(sortedRes,changes, debug) :
    
    new_sortedRes = copy.deepcopy(sortedRes)
    to_build_array = []
    for level in range(0,len(new_sortedRes)) :
        for df in new_sortedRes[level] :
            is_to_build = False
            #Look if Dockerfiles parent is building then set to build
            if df.parent.is_building :
                if not is_to_build :
                    to_build_array.append(df)
                is_to_build = True

            #Look if first layer dockerfile is changed to build their childrens
            #if df.parent.external == True :
            version_number = ""
            if len(df.version.split("_")) > 1 :
                version_number = df.version.split("_")[-1]
            else :
                version_number = df.version
                
            if find_info_from_changesfile(changes,df.name,version_number,debug = debug) :
                if not is_to_build :
                    to_build_array.append(df)
                is_to_build = True
                
            
            #Look if dockerfile is triggered
            if df.is_triggered == True :
                if not is_to_build :
                    to_build_array.append(df)
                is_to_build = True
            
            #Look if parent is building then set it to is_building
            for df_parent in to_build_array :

                if debug :
                    print("{0}:{1} will build does {2} is building ? with parent : {3}:{4} \n".format(df_parent.name,df_parent.version,df.name,df.parent.name,df.parent.version ))
                    
                if df.parent.name == df_parent.name and df.parent.version == df_parent.version:
                    if df_parent.parameters.is_up :
                        if not df_parent.parameters.no_build :
                            df.parent.is_building = True
                    else :
                        df.parent.is_building = True

                    if debug :
                        print(df.name + " will build too because his parent " + df.parent.name +" is building.  \n")
                
                for multistage_parent in df.multistage_parents :
                    if multistage_parent.name == df_parent.name and multistage_parent.version == df_parent.version:
                        multistage_parent.is_building = True
            
            if df.parent.is_building :
                if not is_to_build :
                    to_build_array.append(df)
                is_to_build = True
    
    return new_sortedRes, to_build_array

def sort_pipeline(sortedRes,debug = False):
    pipelines = {}
    for level in range(0,len(sortedRes)) :
        for dockerfile in sortedRes[level] :
            added = False
            if level == 0 :
                folder_name = dockerfile.path.split("/")[0]
                pipeline_name = "pipeline-" + folder_name
                if pipeline_name not in pipelines :
                    pipelines[pipeline_name] = [[dockerfile]]
                else :
                    pipelines[pipeline_name][level].append(dockerfile)
                added = True
            else:
                for pipeline_name in pipelines.keys() :

                    if  len(pipelines[pipeline_name]) - 1 < level :
                        pipelines[pipeline_name].append([])

                    for possible_parent in pipelines[pipeline_name][level - 1] :
                        if dockerfile.parent.name == possible_parent.name and dockerfile.parent.version == possible_parent.version:
                            pipelines[pipeline_name][level].append(dockerfile)
                            added = True
            if not added :
                pipeline_name = "pipeline-others"
                print(dockerfile.name)
                print(dockerfile.parent.version)
                print(level)
                if pipeline_name not in pipelines :
                    pipelines[pipeline_name] = [[dockerfile]]
                else :
                    pipelines[pipeline_name][0].append(dockerfile)

    if (debug) :                       
        for pipeline_name in pipelines.keys() :
            for level in pipelines[pipeline_name]:
                for dockerfile in level :
                    print(pipeline_name)
                    print(pipelines[pipeline_name].index(level))
                    print(dockerfile)
    
    return pipelines

def write_jsonnet_object(df_file, df_obj, index, branch, token, project_id, mode, trigger_variable):
    deploy = True

    df_file.write("\n\t" + df_obj.toJsonnet(mode, JSONNET_BUILD_FUNCTION, CICD_STAGE_BUILD_LABEL, index, branch, "", token, project_id, False, df_obj.parameters.deploy_jenkins, trigger_variable) + ",")
    if ENABLE_DEPLOY and df_obj.parameters.is_up:
        for no_deploy_arg in df_obj.parameters.no_deploy :
            if no_deploy_arg == Deploy.ALL :
                deploy = False
            elif no_deploy_arg == Deploy.PREPROD and branch == PREPROD_KEY :
                deploy = False
            elif no_deploy_arg == Deploy.PROD and branch == PROD_KEY :
                deploy = False
            elif no_deploy_arg == Deploy.DEV and ( branch != PROD_KEY and branch != PREPROD_KEY) :
                deploy = False
        
        if deploy :
            df_file.write("\n\t" + df_obj.toJsonnet(mode, JSONNET_DEPLOY_FUNCTION, CICD_STAGE_BUILD_LABEL, index + 1, branch, "", token, project_id, deploy, df_obj.parameters.deploy_jenkins, trigger_variable) + ",")

def write_jsonnet(dockerfiles, to_build_dict, path, branch, token, project_id, trigger_variable ,debug = False):

    try:
        # Read Dockerfile
        df_file = open(path, 'a')
    except OSError as err:
        # if(debug):
        print("Jsonnet file not found... ({0})".format(err))
        return False
    else:
        # Write Jsonnet beginning
        df_file.write("{\n")

        # Write stages array "beginning"
        df_file.write("\tstages:\n\t\t[")

        # Write first stage
        df_file.write("\n\t\t\t'" + CICD_STAGE_BUILD_LABEL + "0',")
        
        # Write stages list
        for e in range(len(dockerfiles)):
            df_file.write("\n\t\t\t'" + CICD_STAGE_BUILD_LABEL + str(e+1) + "',")

        
        # Write stages array "end"
        df_file.write("\n\t\t]\n\t,")

        # Write jobs header
        df_file.write("\n\n\t// Jobs")

        # Write jobs

        df_file.write("\n\t" + "'empty-job' : { 'script': [ 'echo $CI_COMMIT_MESSAGE' ], 'stage': '" + CICD_STAGE_BUILD_LABEL + "0' }" + ",")

        for df_level in dockerfiles:
            for df_obj in df_level:
                if(to_build_dict["mode"] == "all") :
                    write_jsonnet_object(df_file, df_obj, dockerfiles.index(df_level), branch, token, project_id, to_build_dict["mode"], trigger_variable)
                else :
                    if df_obj in to_build_dict["to_build"] :
                        write_jsonnet_object(df_file, df_obj, dockerfiles.index(df_level), branch, token, project_id, to_build_dict["mode"], trigger_variable)
        
        # Write Jsonnet end
        df_file.write("\n}")

        # Close the file
        df_file.close()

def write_pipelines_jsonnet(pipelines, path, debug = False):

    try:
        # Read Dockerfile
        df_file = open(path, 'a')
    except OSError as err:
        # if(debug):
        print("Jsonnet file not found... ({0})".format(err))
        return False
    else:

        # Write jobs header
        df_file.write("\n\n\t// Jobs")

        # Write jobs

        for pipeline_name in pipelines.keys():
            df_file.write("\n\t'"+pipeline_name+"' : build_pipeline('"+pipeline_name+"'),")
        
        # Write Jsonnet end
        df_file.write("\n}")

        # Close the file
        df_file.close()

def pipelines_write_jsonnet(pipelines, origin_path_jsonnet, branch, token, project_id, debug = False):

    for pipeline_name in pipelines.keys() :
        new_file_path = "cicd-docker/pipelines/" + pipeline_name + ".jsonnet"
        os.makedirs(os.path.dirname("cicd-docker/pipelines/"), exist_ok=True)
        shutil.copy(origin_path_jsonnet, new_file_path)
        write_jsonnet(pipelines[pipeline_name],{'mode':"all",'to_build':[]}, new_file_path, branch, token, project_id, {}, debug = debug)
    
    os.makedirs(os.path.dirname("cicd-docker/pipelines/"), exist_ok=True)
    shutil.copy("cicd-docker/pipelines.jsonnet", "cicd-docker/pipelines/pipelines.jsonnet")
    write_pipelines_jsonnet(pipelines,"cicd-docker/pipelines/pipelines.jsonnet")
