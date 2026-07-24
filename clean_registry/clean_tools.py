from clean_registry.global_vars import *

def check_if_is_dev_branch(branch_to_check):
    check = True
    for branch in BUILDER_PROJECT_BRANCHS :
        if branch_to_check["name"] == branch:
            check = False

    return check

def check_if_is_tag_to_keep(tag_to_check):
    check = False
    for tag in TAG_TO_KEEP :
        if tag in tag_to_check :
            check = True

    return check