import time


class RallyTest():
    """ A container for running and tracking one test in Rally

    An instance of rally_client.RallyClient is required to run this test.
    Note that the design for this class is that many RallyTest(s) should share
    one instance of RallyClient, so that they're all running on the same instance.

    The main method is 'run(<RallyClient object>)'
    """

    def __init__(self, preset_name: str, asset_name: str, dynamic_data: dict = {}):
        assert preset_name, 'Must specify a test preset name'
        assert asset_name, 'Must specify an asset to run the test on'
        self.preset_name = preset_name
        self.asset_name = asset_name
        self.dynamic_preset_data = {}
        if dynamic_data:
            assert type(dynamic_data) is dict, 'Dynamic preset data must be '\
                'a valid dict. (Got {})'.format(str(dynamic_data))
            self.dynamic_preset_data = dynamic_data

        self.job_id = ''
        self.job_status = ''  # 'Queued', 'Active', 'Complete', 'Error'
        self.job_result = ''  # we want 'Pass'
        self.job_lookup_secs = 10
        self.job_lookup_tries = 6

        self.test_completed = False
        self.debug = {
            'job_creation_response': {},
            'job_creation_response_code': 0
        }
        self.error_msg = ''
        self.error_trace_uri = ''
        self.log_messages = []

    def create_job_request_data(self) -> dict:
        return {
            "data": {
                "type": "jobs",
                "attributes": {
                    "dynamicPresetData": self.dynamic_preset_data
                },
                "relationships": {
                    "asset": {
                        "data": {
                            "type": "assets",
                            "attributes": {"name": "{}".format(self.asset_name)}
                        }
                    },
                    "preset": {
                        "data": {
                            "type": "presets",
                            "attributes": {"name": "{}".format(self.preset_name)}
                        }
                    }
                }
            }
        }

    def create_job(self, rally_client_object) -> bool:
        """ POST the test job to the environment set up in the rally client object
        :param rally_client_object: An instantiation of rally_client.RallyClient
        """
        job_response, http_status = rally_client_object.post_job(self.create_job_request_data())
        self.debug['job_creation_response'] = job_response
        self.debug['job_creation_response_code'] = http_status
        job_created = False
        if http_status == 201 and job_response.get('data').get('id'):
            self.job_id = job_response.get('data').get('id')
            self.job_status = job_response.get('data').get('attributes').get('status')
            self.job_result = job_response.get('data').get('attributes').get('result')
            job_created = True

        return job_created

    def follow_job(self, rally_client_object):
        """ Loop until the job is done; timeout after 1 minute """
        tries = 0
        while not self.job_completed() and tries < self.job_lookup_tries:
            time.sleep(self.job_lookup_secs)
            job_response, http_code = rally_client_object.get_job(self.job_id)
            if http_code == 200 and job_response.get('data').get('attributes'):
                self.job_status = job_response.get('data').get('attributes').get('status')
                self.job_result = job_response.get('data').get('attributes').get('result')
            tries = tries + 1

    def job_completed(self) -> bool:
        return self.job_status == 'Complete' or self.job_status == 'Error'

    def run(self, rally_client_object):
        """ Complete a test and store state
        :param rally_client_object: An instantiation of rally_client.RallyClient
        Examine the state of this instance with '.test_completed'
        """
        try:
            pretest_status_msg = '+ Pre-test : Find {} in env {} ...'.format(
                self.asset_name, rally_client_object.settings.get('endpoint')
            )
            
            assert rally_client_object.check_asset_exists(self.asset_name), \
                'The test asset {} was not found in env {}'.format(
                    self.asset_name, rally_client_object.settings.get('endpoint')
                )
            assert rally_client_object.check_preset_exists(self.preset_name), \
                'The test preset {} was not found in env {}'.format(
                    self.preset_name, rally_client_object.settings.get('endpoint')
                )
            pretest_status_msg = pretest_status_msg + ("OK")
            assert (self.create_job(rally_client_object)), 'Failed creating job for test {}'.format(self.preset_name)
            assert self.job_id, 'No job ID was attached to this test, but the job was created.'
            assert self.job_status, 'No job status was attached to this test, but the job was created.'
            self.follow_job(rally_client_object)

            # Check if we timed out, or succeeded
            
            if self.job_status != 'Complete' or self.job_result != 'Pass':
                rally_error = rally_client_object.get_job_error(self.job_id)
                curated_error = self.trim_error(rally_error)
                raise RallyTestFailure(curated_error)
            else:
                self.test_completed = True

        except RallyTestFailure as e:
            self.error_msg = str(e)
            self.error_trace_uri = self.create_trace(rally_client_object)
        except AssertionError as e:
            self.error_msg = str(e)
        except Exception as e:
            print('UNEXPECTED: {}'.format(str(e)))
            self.error_msg = str(e)

    def trim_error(self, api_text_response):
        """ Return just the first line """
        return api_text_response.split("\n")[0]

    # def eval_end_of_test(self):
    #     """ Return error from Rally, and construct trace, if needed """
    #     curated_error = ''
    #     trace = ''
    #     if self.job_status != 'Complete' or self.job_result != 'Pass':
    #         rally_error = rally_client_object.get_job_error(self.job_id)
    #         curated_error = self.trim_error(rally_error)
    #         # print("FAIL: ", end="", flush=True)
    #         trace = 'https://{hostname}/jobs/{job_id}/artifacts/error'.format(
    #             hostname=rally_client_object.settings.get('endpoint'),
    #             job_id=self.job_id
    #         )
    #     return curated_error, trace

    def create_trace(self, rally_client_object):
        return '{hostname}/jobs/{job_id}/artifacts/error'.format(
            hostname=rally_client_object.settings.get('endpoint'),
            job_id=self.job_id
        )

    def log(self, message):
        """ Track log messages and prints for debugging """
        self.log_messages.append(message)


class RallyTestFailure(Exception):
    pass


"""
job_creation_response = {
    "data": {
        "attributes": {
            "category": "Evaluate",
            "clientResourceId": null,
            "completedAt": null,
            "cost": 0,
            "currencyType": "USD",
            "deadline": 1589565111000,
            "dynamicPresetData": {},
            "estimatedCost": 0,
            "events": [],
            "holdUntil": null,
            "percentComplete": 0,
            "phase": null,
            "phaseCount": 1,
            "priority": "PriorityNorm",
            "providerTypeName": "SdviEvaluate",
            "queuedAt": 1593541745025,
            "result": null,
            "retryCount": null,
            "startedAt": null,
            "state": "Queued",
            "status": "Queued",
            "updatedAt": 1593541745114
        },
        "id": "70831ebb-7e6f-4450-937a-0fc7e82bc74c",
        "links": {
            "self": "https://your-hostname.sdvi.com/api/v2/jobs/70831ebb-7e6f-4450-937a-0fc7e82bc74c"
        },
        "relationships": {
            "asset": {
                "data": {
                    "id": "21604",
                    "type": "assets"
                },
                "links": {
                    "self": "https://your-hostname.sdvi.com/api/v2/assets/21604"
                }
            },
            "creator": {
                "data": {
                    "id": "173",
                    "type": "users"
                },
                "links": {
                    "self": "https://your-hostname.sdvi.com/api/v2/users/173"
                }
            },
            "movie": {
                "data": {
                    "id": "21604",
                    "type": "movies"
                },
                "links": {
                    "self": "https://your-hostname.sdvi.com/api/v2/movies/21604"
                }
            },
            "preset": {
                "data": {
                    "id": "2242",
                    "type": "presets"
                },
                "links": {
                    "self": "https://your-hostname.sdvi.com/api/v2/presets/2242"
                }
            },
            "provider": {
                "data": null
            },
            "replacementJob": {
                "data": null
            },
            "retriedJob": {
                "data": null
            },
            "workflow": {
                "data": null
            }
        },
        "type": "jobs"
    }
}
"""
