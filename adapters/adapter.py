import requests


class RallyClient():

    def __init__(self, hostname, RALLY_API_KEY):
        self.settings = self.rally_requests_settings(hostname, RALLY_API_KEY)
        self.hostname = hostname

    def rally_requests_settings(self, hostname: str, RALLY_API_KEY: str):
        assert hostname, 'Must specify a hostname like: yourcompany-uat.sdvi.com, without https://'
        assert RALLY_API_KEY, 'Must supply an API key'
        return {
            "endpoint": "https://{}/api/v2".format(hostname),
            "headers": {
                "Accept": "*/*",
                "Content-Type": 'application/vnd.api+json',
                "Authorization": "Bearer {}".format(RALLY_API_KEY)
            }
        }

    def rally_get(self, api_path):

        """ Base method for gets. Always return a debug object for inspection
        :param api_path: String. Something like /media , etc
        :return: dict, int
        """

        url = "{base_url}{api_path}".format(
            base_url=self.settings["endpoint"],
            api_path=api_path
        )
        # print("+ Looking up %s" % url)
        r = requests.get(url, headers=self.settings["headers"], timeout=10)
        try:
            response = r.json()
        except:
            response = r.text
        return response, r.status_code

    def rally_post(self, api_path, post_data):
        url = "{base_url}{api_path}".format(
            base_url=self.settings["endpoint"],
            api_path=api_path
        )
        # print("+ Posting to {}".format(url))

        r = requests.post(url, headers=self.settings["headers"], json=post_data, timeout=10)
        return r.json(), r.status_code

    def post_job(self, job_data):

        assert job_data, 'Must supply a valid '

        return self.rally_post("/jobs", job_data)

    def get_job(self, job_uuid: str):

        assert job_uuid, 'Must supply a job UUID'

        return self.rally_get(
            "/jobs/{uuid}".format(
                uuid=job_uuid
            )
        )

    def get_workflow(self, workflow_uuid: str):

        return self.rally_get("/workflows/{uuid}".format(
            uuid=workflow_uuid
            )
        )

    def post_workflow(self, wf_data):
        return self.rally_post("/workflows", wf_data)

    def check_jobs_complete(self, list_of_job_uuids):

        """ Return True if job statuses exist (not None/null) """
        """
        Cancelled:
            result: Error
            state: Cancelled
            status: Cancelled
        or
            result: Error
            state: Error
            status: Error
        QC OK, Evaluate OK, Analyze OK, Export OK
            result: Pass
            state: Complete
            status: Complete
        Active:
            result: null
            state: Active
            status: Active
        QC Hold
            result: null
            state: Hold
            status: Hold
        Retried:
            result: Error
            state: Retried
            status: Retried
        """
        # API calls return tuples; the first item in tuple is API data
        jobs_api_data_list = [
            self.get_job(job)[0] for job in list_of_job_uuids
        ]
        for job in jobs_api_data_list:
            print(job)
            print(
                "\n\rResult of job {uuid}: {result}".format(
                    uuid=job["data"]["id"],
                    result=job["data"]["attributes"]["result"]
                )
            )
        jobs_are_done = all(
            job["data"]["attributes"]["result"] is not None for job in jobs_api_data_list
        )
        print(
            "\nAll jobs are done: {bool}".format(
                bool=jobs_are_done
            )
        )
        return jobs_are_done

    def check_asset_exists(self, asset_name):
        """ Test whether an asset is found in an instance """
        # GET /assets/:id

        lookup, http_code = self.rally_get('/assets?filter=name={}'.format(asset_name))

        return http_code == 200 and lookup.get('data')

    def check_preset_exists(self, preset_name):
        """ Test whether a preset is found in an instance """
        lookup, http_code = self.rally_get(
            '/presets?filter=name={}'.format(preset_name.replace(' ', '+'))
        )
        return http_code == 200 and lookup.get('data')

    def get_job_error(self, job_id):

        lookup, http_code = self.rally_get(
            '/jobs/{}/artifacts/error'.format(job_id)
        )
        return lookup

    def check_workflow_exists(self, workflow_name) -> bool:
        lookup, http_code = self.rally_get(
            '/workflowRules?filter=name={}'.format(workflow_name)
        )
        return http_code == 200 and lookup.get('data')

    def lookup_job_error(self, job_id: str) -> str:
        lookup, http_code = self.rally_get(
            '/jobs/{}/errorDetails'.format(job_id)
        )
        return lookup

    def get_jobs_by_workflow_v1(self, workflow_id) -> dict:
        """ Look up jobs using a v1.0 API call """
        url = "{base_url}{api_path}".format(
            base_url="https://{}/api/v1.0".format(self.hostname),
            api_path='/jobs?filter={{%22workflowBaseId%22:%22{}%22}}&sorting={{%22queuedAt%22:%22asc%22}}&count=20'.format(str(workflow_id))
        )
        r = requests.get(url, headers=self.settings["headers"])
        try:
            response = r.json()
        except:
            response = r.text
        return response, r.status_code

    def get_asset(self, asset_id) -> dict:
        lookup, http_code = self.rally_get(
            '/assets/{}'.format(asset_id)
        )
        return lookup

    def get_job_artifact_output(self, job_id):

        lookup, http_code = self.rally_get(
            '/jobs/{}/artifacts/output'.format(job_id)
        )
        return lookup
