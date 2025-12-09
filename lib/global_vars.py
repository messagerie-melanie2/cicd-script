# coding=utf-8
import argparse
import requests
import os
import yaml
import json
import logging
import subprocess
import sys
import fnmatch
from datetime import date, timedelta
from environs import Env

#=======================================================#
#================== Global parameters ==================#
#=======================================================#
env = Env()

ACCEPTED_STATUS_CODE = [200,201,202]

GITLAB_URL = os.environ.get('GITLAB_PROTOCOL',"https://") + os.environ.get('GITLAB_DOMAIN',"")

#=======================================================#
#============== Trigger Global parameters ==============#
#=======================================================#
TRIGGER_VARIABLE_CONFIGURATION_KEY_DEFAULT = 'TRIGGER_CONFIGURATION'
SETUP_TRIGGER_ARGUMENTS_DEFAULT = {'all': 'trigger_files,branchs_only_trigger,branchs_mapping', 'gitlab': 'focus_trigger', 'jenkins': 'additional_params,token_name'}

TRIGGER_VARIABLE_CONFIGURATION_KEY = env.json('SETUP_VARIABLE_CONFIGURATION_KEY',TRIGGER_VARIABLE_CONFIGURATION_KEY_DEFAULT)
SETUP_TRIGGER_ARGUMENTS = env.json('SETUP_TRIGGER_ARGUMENTS',SETUP_TRIGGER_ARGUMENTS_DEFAULT)
