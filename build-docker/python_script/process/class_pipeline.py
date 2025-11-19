# coding=utf-8
from global_vars import *
from process.class_pipeline_tools import add_branch_to_version,convert_multistage_parents_version_to_kaniko_arg,create_job_needs

#=======================================================#
#======================= Classes =======================#
#=======================================================#

##### DTOs classes

class InfoFromPath:
    """Class containing information that we take from the path"""

    # Number of elements
    count = 4

    # Extract elements from Regex result groups
    def __init__(self, reg_groups):
            self.path = reg_groups.group(1)
            self.file = reg_groups.group(2)
            self.image_name = reg_groups.group(3)
            self.image_version_number = reg_groups.group(4)

    def __str__(self):
        return "InfoFromPath=[path: '{0}', file: '{1}', image_name: '{2}', image_version_number: '{3}']".format(self.path, self.file, self.image_name, self.image_version_number)

class InfoFromDockerfile:
    """Class containing information that we take from the Dockerfile"""

    # Number of elements
    count = 6

    # Extract elements from Args result groups
    def __init__(self, args):
        self.parent_version_default = args[0]
        self.parent_version_replace_with = args[1]
        self.image_version_replace = args[2]
        self.parent_name = args[3]
        self.parent_external = args[4]
        self.multistage_parents = args[5]

    def __str__(self):
        return "InfoFromDockerfile=[parent_version_default: '{0}', parent_version_replace_with: '{1}', image_version_replace: '{2}', parent_name: '{3}', parent_external: '{4}', multistage_parents: '{5}']".format(self.parent_version_default, self.parent_version_replace_with, self.image_version_replace, self.parent_name, self.parent_external,self.multistage_parents)

##### Objects classes
class Deploy(Enum):
    NONE = 0
    DEV = 1
    PREPROD = 2
    PROD = 3
    ALL = 4
 
class Parameters:
    """Class containing Dockerfile's parameters information"""

    def __init__(self, is_up, parent_version, no_build, no_repo, no_deploy, deploy_jenkins, variables, multistage_parents):
        self.is_up = is_up
        self.parent_version = parent_version
        self.no_build = no_build
        self.no_repo = no_repo
        self.no_deploy = no_deploy
        self.deploy_jenkins = deploy_jenkins
        self.variables = variables
        self.multistage_parents = multistage_parents

    def __str__(self):
        return "Parameters with parent_version '{0}', no_build is {1} and  no_repo is {2}".format(self.parent_version, str(self.no_build), str(self.no_repo))
    
class Parent:
    """Class containing Dockerfile's parent information"""

    def __init__(self, name, version, external,is_building,repository_id):
        self.name = name
        self.version = version
        self.external = external
        self.is_building = is_building
        self.repository_id = repository_id

    def __str__(self):
        ext = "" if self.external else "not "
        return "Parent with name '{0}' and version {1} which is {2}external".format(self.name, self.version, ext)

class MultiStageParent(Parent):
    """Class containing Dockerfile's multistage parent information"""
    def __init__(self, name, version, external,is_building,repository_id,alias,have_parameters,project_dependency,files_dependency):
        self.alias = alias
        self.have_parameters = have_parameters
        self.project_dependency = project_dependency
        self.files_dependency = files_dependency
        super().__init__(name=name, version=version, external=external, is_building=is_building, repository_id=repository_id)

    def __str__(self):
        ext = "" if self.external else "not "
        return "MultiStageParent with name '{0}' and version {1} which is {2}external".format(self.name, self.version, ext)
        
class Dockerfile:
    """Class containing Dockerfile information"""

    def __init__(self, path, name, parent, multistage_parents, parameters, version, branch, is_changed, is_triggered, kaniko_args):
        self.path = path
        self.name = name
        self.version = version
        self.parent = parent
        self.multistage_parents = multistage_parents
        self.parameters = parameters
        self.branch = branch
        self.is_changed = is_changed
        self.is_triggered = is_triggered
        self.kaniko_args = kaniko_args
    
    def __str__(self):
        return "Dockerfile with name '{0}', version '{1}', parent '{2}' and path '{3}' with branch '{4}'".format(self.name, self.version, self.parent, self.path, self.branch)

    def toJsonnet(self, mode, method, stage, level, branch, suffix, token, project_id, deploy, deploy_jenkins, trigger_variable):
        
        # Ajout du nom de la branche dans le tag de version
        version = self.version
        if(branch != ""):
            version = "{0}-{1}".format(self.version, branch)
            self.parent = add_branch_to_version(self.parent,branch,token,project_id, trigger_variable)
            new_multistage_parents = []
            for multistage_parent in self.multistage_parents:
                if multistage_parent.have_parameters :
                    multistage_parent = add_branch_to_version(multistage_parent,branch,token,project_id, {})
                    self.kaniko_args += convert_multistage_parents_version_to_kaniko_arg(multistage_parent,True)
                new_multistage_parents.append(multistage_parent)
                self.multistage_parents = new_multistage_parents
        else:
            for multistage_parent in self.multistage_parents:
                if multistage_parent.have_parameters :
                    self.kaniko_args += convert_multistage_parents_version_to_kaniko_arg(multistage_parent,True)

        # Build result string
        parent_str = "{{name: '{0}', version: '{1}', external: {2}, is_building: {3}}}".format(self.parent.name, self.parent.version, str(self.parent.external).lower(), str(self.parent.is_building).lower())

        job_needs = create_job_needs(self.parent,self.multistage_parents,mode)

        # return "'{2}{7}{9}{10}' : {0}('{8}{1}', '{2}', '{3}', {{name: '{4}', external: {5}}}, '{6}')".format(method, level, self.name, self.path, self.parent.name, str(self.parent.external).lower(), version, suffix, stage, DOCKER_IMAGE_TAG_SEPARATOR, self.version_number)
        #
        if not deploy :
            return "'{2}:{5}{6}' : {0}('{7}{1}', '{2}', '{3}', {4}, '{5}', '{8}', {9}, {10}, {11}, '{12}')".format(method, level, self.name, self.path, parent_str, version, suffix, stage, self.branch, str(self.is_changed).lower(), str(self.is_triggered).lower(),job_needs, self.kaniko_args)
            # 'php-mce-rcube' : build_docker(0, 'php-mce-rcube', 'php/php-mce-rcube', {name: 'registry/php-mce-generic', external: false, is_building: false}, '7.3-fpm_1.0', 'prod', 'True', 'False', 'debian-mce-generic'),
        else :
            return "'deploy-{2}:{5}{6}' : {0}('{7}{1}', '{2}', '{3}', {4}, '{5}', '{8}', {9}, {10}, '{2}:{5}{6}', '{11}')".format(method, level, self.name, self.path, parent_str, version, suffix, stage, self.branch, str(self.is_changed).lower(), str(self.is_triggered).lower(), deploy_jenkins)
