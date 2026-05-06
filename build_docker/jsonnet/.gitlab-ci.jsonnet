local build_docker(payload, job_needs) =
{
  stage: payload.stage,
  //
  rules:
      if (payload.parent.is_building == 1 || payload.is_triggered == 1 || payload.is_changed == 1)
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
    NAME: payload.name,
    VERSION: payload.version,
    PARENT_VERSION: payload.parent.version,
    BUILD_PATH: payload.path,
    BUILD_BRANCH: payload.branch,
    #
    TAG: "${CI_REGISTRY}/${CI_PROJECT_NAMESPACE}/${CI_PROJECT_NAME}/${NAME}:${VERSION}",
    OTHER_DOCKER_ARGS: payload.docker_args,
    ALLOWED_PUSH: payload.allowed_push,
    BUILDKITD_FLAGS: "--oci-worker-no-process-sandbox",
  } + if payload.latest == 1 then {TAG_LATEST: "${CI_REGISTRY}/${CI_PROJECT_NAMESPACE}/${CI_PROJECT_NAME}/${NAME}:latest",} else {}
   + if payload.registry_push != {} then {CI_REGISTRY: payload.registry_push.name,CI_REGISTRY_USER: payload.registry_push.username,CI_REGISTRY_PASSWORD: payload.registry_push.password,} else {}
   + if payload.registry_pull != {} then {CI_PULL_REGISTRY: payload.registry_pull.name,CI_PULL_REGISTRY_USER: payload.registry_pull.username,CI_PULL_REGISTRY_PASSWORD: payload.registry_pull.password,} else {}
   ,
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
      ('echo Building docker image ' + payload.name + ' of stage ' + payload.stage + ' and parent ' + payload.parent + ' -- path : ' + payload.path + ' -- version : ' + payload.version + '.'),
      #
      # Call the entrypoint script, after going in the right directory (gitlab-runner starts in a directory that's not the workdir)
      # Kaniko Builder Entrypoint
      '/builder/entrypoint.sh',
      #'cp /tmp/${NAME}_metadata.json ./${NAME}_metadata.json',
      #'cat ./${NAME}_metadata.json'
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
    paths:['./${NAME}_metadata.json']
  },
};
local deploy_docker(payload) =
{
  stage: payload.stage,
  //
  rules:
    if (payload.parent.is_building == 1 || payload.is_triggered == 1 || payload.is_changed == 1)
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
    job: payload.job_to_deploy,
  },
  //
  variables:
  {
    NAME: payload.name,
    VERSION: payload.version,
    TAG: "${CI_REGISTRY}/${CI_PROJECT_NAMESPACE}/${CI_PROJECT_NAME}/${NAME}:${VERSION}",
    JENKINS_TOKEN: "${JENKINS_TOKEN}",
    JENKINS_URL: payload.deploy_jenkins,
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

