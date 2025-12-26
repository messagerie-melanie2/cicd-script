/**
 * Function to check if a string 's' contains a specified substring 
 */
//local strContains(s, substr) = std.length(std.findSubstr(substr, s)) > 0;
local strContains(s, substr) = std.findSubstr(substr, s) != [];

/**
 * Function to ...
 */
local build_docker(stage, name, path, parent, version, branch, is_changed, is_triggered, job_needs, docker_args) =
{
  stage: stage,
  //
  rules:
      if (parent.is_building == true || is_triggered == true || is_changed == true)
      then 
      [{
        when: 'on_success'
      }]
      else
      [{
        # Any commit pushed with 'ci-all' will trigger all jobs
        #
        # In order to handle web/scheduled pipelines, a line is needed in .gitlab-ci.yml
        # @see https://docs.gitlab.com/ee/ci/pipelines/downstream_pipelines.html#pass-cicd-variables-to-a-downstream-pipeline
        #
        'if': '$CICD_COMMIT =~ /.*ci-all.*/',
        when: 'on_success'
      }]
  ,
  //
  tags: std.split(std.extVar('RUNNER_TAGS'), ','),
  //
  needs:job_needs,
  //
  variables:
  {
    NAME: name,
    // VERSION: if(branch != "") then version else (version + "-" + branch),
    VERSION: version, //std.strReplace(version, "_", "-"),
    PARENT_VERSION: parent.version,
    BUILD_PATH: path,
    BUILD_BRANCH: branch,
    #
    TAG: "${CI_REGISTRY}/${CI_PROJECT_NAMESPACE}/${CI_PROJECT_NAME}/${NAME}:${VERSION}",
    OTHER_DOCKER_ARGS: docker_args,
  },
  image:
  {
      # name: "${CI_REGISTRY}/${CI_PROJECT_NAMESPACE}/cicd-docker/kaniko-executor:v1.9.1-debug",
      name: "${REGISTRY_DOMAIN}${CICD_NAMESPACE}${CICD_BUILDER_PATH}:${CICD_BUILDER_TAG}",
      entrypoint: [""],
  },
  //
  before_script:
    [
      'source $BEFORE_SCRIPT_PATH',
    ]
  ,
  //
  script:
    [
      'echo $RUNNER_TAGS',
      #
      # Log which image we are building
      #
      ('echo Building docker image ' + name + ' of stage ' + stage + ' and parent ' + parent + ' -- path : ' + path + ' -- version : ' + version + '.'),
      #
      # Call the entrypoint script, after going in the right directory (gitlab-runner starts in a directory that's not the workdir)
      # Kaniko Builder Entrypoint
      '$KBE'
    ]
  ,
  retry:
  {
    max: 2,
    when: ['script_failure']
  }
  ,
  artifacts:
  {
    expire_in: '1 hours',
    paths:['cicd-docker/${NAME}/']
  },
};
local deploy_docker(stage, name, path, parent, version, branch, is_changed, is_triggered, job_to_deploy, deploy_jenkins) =
{
  stage: stage,
  //
  rules:
    if (parent.is_building == true || is_triggered == true || is_changed == true)
    then 
    [{
      when: 'on_success'
    }]
    else
    [{
      # Any commit pushed with 'ci-all' will trigger all jobs
      #
      # In order to handle web/scheduled pipelines, a line is needed in .gitlab-ci.yml
      # @see https://docs.gitlab.com/ee/ci/pipelines/downstream_pipelines.html#pass-cicd-variables-to-a-downstream-pipeline
      #
      'if': '$CICD_COMMIT =~ /.*ci-all.*/',
      when: 'on_success'
    }]
  ,
  //
  tags: std.split(std.extVar('RUNNER_TAGS'), ','),
  //
  needs:
  {
    job: job_to_deploy,
  },
  //
  variables:
  {
    NAME: name,
    VERSION: version,
    TAG: "${CI_REGISTRY}/${CI_PROJECT_NAMESPACE}/${CI_PROJECT_NAME}/${NAME}:${VERSION}",
    JENKINS_TOKEN: "${JENKINS_TOKEN}",
    JENKINS_URL: deploy_jenkins,
  },
  image:
  {
      name: "${REGISTRY_DOMAIN}${CICD_NAMESPACE}${CICD_DEPLOY_PATH}:${CICD_DEPLOY_TAG}",
      entrypoint: [""],
  },
  //
  script:
    [
      '/usr/local/bin/yamlentrypoint.py --yamldir /usr/local/etc/yaml.d',
    ]
  ,
  retry:
  {
    max: 2,
    when: ['script_failure']
  }
  ,
};

