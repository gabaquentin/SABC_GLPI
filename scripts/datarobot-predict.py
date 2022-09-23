
"""Usage:
    python datarobot-predict.py <input-file.csv> <output-file.csv>

We highly recommend that you update SSL certificates with:
    pip install -U "urllib3[secure]" certifi

Details: https://app.datarobot.com/docs/predictions/batch/batch-prediction-api/index.html
"""
import sys
import logging
import argparse
import datarobot as dr

API_KEY = 'NjMyODkwZGNlNTFhNmNlNTZmOGFlMWEyOmVQRUkyZnFsL2xIL2RZT1FYNXhWQzdRMHRmMjRLVW40TmRYdWR5YytxaTA9'
BATCH_PREDICTIONS_URL = 'https://app2.datarobot.com/api/v2'
DEPLOYMENT_ID = '6329929cd452ce5ad78adfe7'


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s %(filename)s:%(lineno)d %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__, usage='python %(prog)s <input-file.csv> <output-file.csv>'
    )
    parser.add_argument(
        'input_file', help='Input CSV file with data to be scored.'
    )
    parser.add_argument(
        'output_file', help='Output CSV file with the scored data.'
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        default=False,
        dest="ssl_insecure",
        help="Skip SSL certificates verification for HTTPS "
             "endpoints. Using this parameter is not secure and is not recommended. "
             "This switch is only intended to be used against known hosts using a "
             "self-signed certificate for testing purposes. Use at your own risk.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    input_file = args.input_file
    output_file = args.output_file
    ssl_insecure = args.ssl_insecure

    logger.info(
        "Creating Batch Prediction job for deployment ID {deployment_id}".format(
            deployment_id=DEPLOYMENT_ID,
        )
    )

    dr.Client(
        endpoint=BATCH_PREDICTIONS_URL,
        token=API_KEY,
        ssl_verify=not ssl_insecure,
        user_agent_suffix='IntegrationSnippet-ApiClient'
    )

    job = dr.BatchPredictionJob.score(
        deployment=DEPLOYMENT_ID,
        intake_settings={
            'type': 'localFile',
            'file': input_file,
        },
        output_settings={
            'type': 'localFile',
            'path': output_file,
        },
        # If explanations are required, uncomment the line below
        # max_explanations=3,
        # Uncomment this for Prediction Warnings, if enabled for your deployment.
        # prediction_warning_enabled=True
    )

    job.wait_for_completion()

    logger.info(
        "Finished Batch Prediction job ID {job_id} for deployment ID {deployment_id}. "
        "Results downloaded to {output_file}.".format(
            job_id=job.id, deployment_id=DEPLOYMENT_ID, output_file=output_file
        )
    )

    return 0

if __name__ == '__main__':
    sys.exit(main())

