# RampleFish - Remotely run code in SDVI Rally instances

This tool is for developers who are working on integrations and feature code within their company's instance of the SDVI Rally media management application.

This tool can be configured to remotely run SDVI Rally Python presets on an SDVI instance, and report the results locally. It is an alternative to using the SDVI Rally user interface to do repetitive development work.

It currently does _not_ do workflow testing or tracking (yet).

## Why

I created this as a way to speed up my local development process. I had Python code in the Rally SDVI environment, which was a collection of unit tests for another batch of feature code I developed, also hosted there. Using this tool, I was able to make code changes locally, push the changes to the remote SDVI instance from my command line, and immediately get feedback by using this tool to run the code and see the output.

This saved me a lot of time as the trace error reported back provided good hints as to what I needed to fix locally, without going into the application's UI.


## Features

- Self-checks: Each test will first check if its preset exists in the target environment, and also check if the test asset exists
- Retry API errors: Each test times out after 1 minute if the status never reaches 'Complete' or 'Pass'
- Test output similar to other test suites
- Run tests asynchronously in batches
- send optional dynamic preset data with tests
- Make test timeout period and number of retries configurable via config file
- Report specific job-related errors locally


## Usage

Syntax:
`python rample.py config_file.json`

Alternately, you can install this package and use `rample config_file.json` to call it.

See `sample_instance_config.json`; the config file holds the hostname for the Rally instance, a default asset to run presets on, and a list of presets with optional specific assets that a test should be run with.

Be sure to add a valid API key to the config file. For each instance, create a separate configuration file (ex: one for your QA instance, one for user acceptance testing)

## Sample config file
```
{
    "env_hostname": "your-company-dev.sdvi.com",
    "default_test_asset": "194228_007",
    "api_key": "secret_api_key",
    "tests": [
        {
            "name": "Sample Preset 1",
            "asset": "",
            "dynamicPresetData": {
                "foo": "bar"
            },
            "enabled": true
        }
    ]
}
```
Breakdown of an entry in the list of tests:

- `name`: (Required) The name of the preset as it is shown in Rally. 
        For __preset__ testing, this is the name of the preset.
- `asset`: (Optional) A specific asset to run this preset on. Otherwise, the default test asset will be used
- `dynamicPresetData`: (Optional) Any dynamic data that should be set when running this preset.
- `enabled`: Set to false to tell the runner to skip that preset


# How it works
The runner relies on SDVI Rally's API to do all the work of running presets.

The runner uses a thread pool to batch presets and workflows asynchronously.

If a preset fails, the runner gets the error details and prints them locally.

## How presets are tested
The preset information is POSTed to Rally as a job via API. If no response is given in a certain time, the preset test is failed. A preset is considered "passed" if the API returns a `Complete` status.

Since jobs are one-offs, the runner only needs to poll one endpoint.

# Rally test runner output

## Example output for a set of presets
    
    START: PRESET: 'Sample Test 2 Fails' ASSET: 'MOVIE_NAME_001'
    START: PRESET: 'Media Tools' ASSET: 'MOVIE_NAME_001'
    START: PRESET: 'Linear Delivery Test' ASSET: 'MOVIE_NAME_001'
    ...
    Presets: 1 passed, 3 total
    Summary of preset failures:
    {   'asset': 'MOVIE_NAME_001',
        'error': 'The test preset Sample Test 2 Fails was not found in env '
                 'DEV',
        'name': 'Sample Test 2 Fails',
        'trace': ''}
    {   'asset': 'MOVIE_NAME_001',
        'error': 'NameError: name `statusUpdate` is not defined',
        'name': 'Linear Delivery Test',
        'trace': 'https://instance-qa.sdvi.com/api/v2/jobs/973d3a51-bbe1-4f1f-8ea9-d654c81c5f39/artifacts/error'}


## To do

- Support for multiple devs running the same tests; dynamic creation of temporary presets (one-time/ephemeral)
