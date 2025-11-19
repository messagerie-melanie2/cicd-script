#!/bin/bash

# when a command fails, bash exits instead of continuing with the rest of the script.
# This will make the script fail, when accessing an unset variable
#This will ensure that a pipeline command is treated as failed, even if one command in the pipeline fails.

# Makes the script fail/exit when
#   - A command fails
#   - Accessing an unset variable
#   - One command in a pipeline fails
# set -o errexit
# set -o nounset 
# set -o pipefail

# # Global variables
readonly PROGNAME=$(basename $0)
readonly PROGDIR=$(readlink $(dirname $0))
readonly ARGS="$@"

# Global variables from ENV
#
readonly CICD_COMMIT=${CICD_COMMIT}
readonly CI_REGISTRY=${CI_REGISTRY}
readonly CI_REGISTRY_USER=${CI_REGISTRY_USER}
readonly CI_REGISTRY_PASSWORD=${CI_REGISTRY_PASSWORD}
readonly DOCKERHUB_USER=${DOCKERHUB_USER}
readonly DOCKERHUB_TOKEN=${DOCKERHUB_TOKEN}
readonly http_proxy=${http_proxy}
readonly https_proxy=${https_proxy}
readonly NO_PROXY=${NO_PROXY}
readonly NAME=${NAME}
readonly REGISTRY_MIRROR=${REGISTRY_MIRROR}
readonly PARENT_VERSION=${PARENT_VERSION}
readonly BUILD_BRANCH=${BUILD_BRANCH}
readonly CI_JOB_TOKEN=${CI_JOB_TOKEN}
readonly OTHER_KANIKO_ARGS=${OTHER_KANIKO_ARGS}



# Main script instructions
main()
{
    # Option to build but push only if real modifications are found
    # 'if echo $CI_COMMIT_MESSAGE | grep -q "ci-clean-debug"; then export DEBUG=true; fi',
    if echo $CICD_COMMIT | grep -q "ci-check-before-push"; then export CHECK_BEFORE_PUSH=true; fi
    #
    if echo $OTHER_KANIKO_ARGS | grep -q "no-push"; then export CHECK_BEFORE_PUSH=false; fi
    
    echo $CHECK_BEFORE_PUSH
    
    # Setup Kaniko configuration elements
    ## Create directory for Kaniko config
    mkdir -p /kaniko/.docker
    #
    ## Build Kaniko config JSON as string (alternative to auth: {'username':'${CI_REGISTRY_USER}','password':'${CI_REGISTRY_PASSWORD}'})
    KANIKO_CFG="{'auths':{'$CI_REGISTRY':{'auth':'$(echo -n $CI_REGISTRY_USER:$CI_REGISTRY_PASSWORD|base64 -w 0)'},'https://index.docker.io/v1/':{'auth':'$(echo -n $DOCKERHUB_USER:$DOCKERHUB_TOKEN|base64 -w 0)'}},'proxies':{'default':{'httpProxy':'$http_proxy','httpsProxy':'$https_proxy','noProxy':'$NO_PROXY'}}}"
    #
    ## Replace all simple quotes with double quotes (with Jsonnet-adapted syntax : \' becomes \\\' )
    KANIKO_CFG=$(echo "$KANIKO_CFG" | tr "'" "\"")
    #
    ## Write the config in the appropriate file
    echo $KANIKO_CFG > /kaniko/.docker/config.json
    #
    ## Create a variable to store Kaniko build args (image digest related)
    export KANIKO_DIGEST_BUILD_ARGS="--image-name-tag-with-digest-file "
    export KANIKO_FILE_DIGEST="cicd-docker/$NAME/digest.txt"
    #
    if [ "$REGISTRY_MIRROR" != "" ]
    then
        ## Create a variable to store Kaniko build args (proxy related)
        export KANIKO_PROXY_BUILD_ARGS="--image-name-tag-with-digest-file $KANIKO_FILE_DIGEST --build-arg http_proxy=$http_proxy --build-arg https_proxy=$https_proxy --build-arg no_proxy=$NO_PROXY --registry-mirror $REGISTRY_MIRROR --insecure-registry $REGISTRY_MIRROR"
    else
        ## Create a variable to store Kaniko build args (proxy related)
        export KANIKO_PROXY_BUILD_ARGS="--image-name-tag-with-digest-file $KANIKO_FILE_DIGEST --build-arg http_proxy=$http_proxy --build-arg https_proxy=$https_proxy --build-arg no_proxy=$NO_PROXY"
    fi
    #
    ## Create a variable to store Dockerfile build args (image related)
    # TODO : image_version=${version}
    export DOCKER_BUILD_ARGS="--build-arg parent_version=$PARENT_VERSION --build-arg build_branch=$BUILD_BRANCH --build-arg ci_job_token=$CI_JOB_TOKEN $OTHER_KANIKO_ARGS"

    echo $DOCKER_BUILD_ARGS
    #
    ## Create a variable to store the current path
    export BUILD_PWD=$(pwd)
    #
    # # Display Proxy environment variables
    # echo -e "Displaying proxy setup...
    # \r\n -- proxy_url        [] $proxy_url
    # \r\n -- HTTP_PROXY       [] $HTTP_PROXY
    # \r\n -- HTTPS_PROXY      [] $HTTPS_PROXY
    # \r\n -- http_proxy       [] $http_proxy
    # \r\n -- no_proxy         [] $no_proxy
    # \r\n -- NO_PROXY         [] $NO_PROXY 
    # \r\n -- https_proxy      [] $https_proxy "

    #
    # Display Docker environment variables
    echo -e "Building docker image...
    \r\n -- Image   [] $NAME
    \r\n -- Version [] $VERSION
    \r\n -- From    [] $BUILD_PATH
    \r\n -- Tag     [] $TAG "
}

# Run the script
main $ARGS