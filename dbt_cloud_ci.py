import enum
import os
import time
import re

import requests

# capture environment variables from the bitbucket-pipelines configuration yml
ACCOUNT_ID = os.getenv("DBT_CLOUD_ACCOUNT_ID")
PROJECT_ID = os.getenv("DBT_CLOUD_PROJECT_ID")
JOB_ID = os.getenv("DBT_CLOUD_JOB_ID")
API_KEY = os.getenv("DBT_CLOUD_API_TOKEN")
BITBUCKET_BRANCH = os.getenv(
    "BITBUCKET_BRANCH"
)  # built into the bitbucket pull request environment during runtime
# snowflake schema safe name by replacing all non-word or non-number characters with an underscore
BITBUCKET_BRANCH_SAFE_NAME = re.sub(r"[^\w\s]", "_", BITBUCKET_BRANCH)
# set variable for commit id, commit id shown in gui is shorted to 7 chars, so same behaviour is mirrored here
BITBUCKET_COMMIT_ID = os.getenv("BITBUCKET_COMMIT")[:7]
# set the ID of the PR
BITBUCKET_PR_ID = os.getenv("BITBUCKET_PR_ID")

# define a class of different dbt Cloud API status responses in integer format
class DbtJobRunStatus(enum.IntEnum):
    QUEUED = 1
    STARTING = 2
    RUNNING = 3
    SUCCESS = 10
    ERROR = 20
    CANCELLED = 30


# trigger the dbt Cloud pull request test job
def _trigger_job() -> int:
    res = requests.post(
        url=f"https://cloud.getdbt.com/api/v2/accounts/{ACCOUNT_ID}/jobs/{JOB_ID}/run/",
        headers={"Authorization": f"Token {API_KEY}"},
        data={
            "cause": f"BitBucket Pull Request",
            "schema_override": f"dbt_cloud_pr_{BITBUCKET_COMMIT_ID}_{BITBUCKET_PR_ID}",
            "git_branch": f"{BITBUCKET_BRANCH}",
        },
    )

    try:
        res.raise_for_status()
    except:
        print(f"API token (last four): ...{API_KEY[-4:]}")
        raise

    response_payload = res.json()
    return response_payload["data"]["id"]


# to be used in a while loop to check on job status
def _get_job_run_status(job_run_id):
    res = requests.get(
        url=f"https://cloud.getdbt.com/api/v2/accounts/{ACCOUNT_ID}/runs/{job_run_id}/",
        headers={"Authorization": f"Token {API_KEY}"},
    )

    res.raise_for_status()
    response_payload = res.json()
    return response_payload["data"]["status"]


# main function operator to trigger the job and a while loop to wait for success or error
def run():
    job_run_id = _trigger_job()

    print(f"job_run_id = {job_run_id}")
    visit_url = f"https://cloud.getdbt.com/#/accounts/{ACCOUNT_ID}/projects/{PROJECT_ID}/runs/{job_run_id}/"

    while True:
        time.sleep(5)

        status = _get_job_run_status(job_run_id)

        print(f"status = {status}")

        if status == DbtJobRunStatus.SUCCESS:
            print(f"Success! Visit URL: {visit_url}")
            break
        elif status == DbtJobRunStatus.ERROR or status == DbtJobRunStatus.CANCELLED:
            raise Exception(f"Failure! Visit URL: {visit_url}")


if __name__ == "__main__":
    run()