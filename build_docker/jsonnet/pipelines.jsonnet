/**
 * Function to ...
 */ 

local build_pipeline(name) =
{
  //
  stage: 'launch',
  //
  needs:
    [{
      job: 'get-artifacts',
    }],
  //
  variables:
  {
    PIPELINE_NAME: name,
    PARENT_PIPELINE_ID: '$PARENT_PIPELINE_ID',
    CICD_COMMIT: "${CICD_COMMIT}",
  },
  trigger:
  {
    include:
    [{
        artifact: "${CI_PIPELINE_YAML_FOLDER_PATH}/${PIPELINE_NAME}.yaml",
        job: 'get-artifacts',
    }],
    strategy: 'depend',
    forward:
      {
        pipeline_variables: true,
      }
  },
};

{
	stages:
		[
      'artifacts',
			'launch',
		]
	,
  'get-artifacts':
  {
      stage: 'artifacts',
      //
      needs:
          [{
          pipeline: '$PARENT_PIPELINE_ID',
          job: 'convert-jsonnet-to-json',
          }],
      //
      image: {name:"ruby:2.6",},
      script:
      [
          'echo PARENT_PIPELINE_ID - ${PARENT_PIPELINE_ID}',
          'export -p',
          'ls',
      ],
      artifacts:
      {
          expire_in: '6 hours',
          paths:
          [
          'cicd-script/' ,
          ]
      },
  },

