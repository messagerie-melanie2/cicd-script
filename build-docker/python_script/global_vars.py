import re
import os
import shutil
import argparse
import requests
import copy
import yaml
import json
import fnmatch
from enum import Enum
from environs import Env

#=======================================================#
#================== Global parameters ==================#
#=======================================================#

env = Env()

DOCKER_FILE_NAME = os.environ.get('DOCKER_FILE_NAME',"Dockerfile")
NOBUILD_FILE_NAME = os.environ.get('NOBUILD_FILE_NAME',"NO_BUILD")
PARENT_VERSIONS_FILE_NAME = os.environ.get('PARENT_VERSIONS_FILE_NAME',"parent_versions")
PARAMETERS_FILE_NAME = os.environ.get('PARAMETERS_FILE_NAME',"parameters.yml")
JSONNET_BUILD_FUNCTION = os.environ.get('JSONNET_BUILD_FUNCTION',"build_docker")
JSONNET_DEPLOY_FUNCTION = os.environ.get('JSONNET_DEPLOY_FUNCTION',"deploy_docker")
CICD_STAGE_BUILD_LABEL = os.environ.get('CICD_STAGE_BUILD_LABEL',"build-df")
GIT_MASTER_BRANCH_KEYWORDS = env.list("GIT_MASTER_BRANCH_KEYWORDS",[ "master", "main" ])
DOCKER_IMAGE_HUB_KEYWORD = os.environ.get('DOCKER_IMAGE_HUB_KEYWORD',"official")
DOCKER_IMAGE_TAG_SEPARATOR = os.environ.get('DOCKER_IMAGE_TAG_SEPARATOR',"_")
DOCKER_IMAGES_PARENT_LEVELS = int(os.environ.get('DOCKER_IMAGES_PARENT_LEVELS',15))
NO_BRANCH = os.environ.get('NO_BRANCH',"nobranch")
PREPROD_KEY = os.environ.get('PREPROD_KEY',"preprod")
PROD_KEY = os.environ.get('PROD_KEY',"prod")
RECETTE_KEY = os.environ.get('RECETTE_KEY',"recette")
GITLAB_URL = os.environ.get('GITLAB_PROTOCOL',"https://") + os.environ.get('GITLAB_DOMAIN',"")
REPOSITORIES_WHITELIST = env.list("REPOSITORIES_WHITELIST",[])
ENABLE_DEPLOY = env.bool("ENABLE_DEPLOY",False)
DOCKER_BUILD_ARG_OPTION = os.environ.get('DOCKER_BUILD_ARG_OPTION',"--opt build-arg:")