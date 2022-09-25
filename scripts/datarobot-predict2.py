
"""Usage:
    python datarobot-predict.py <input-file.csv> <output-file.csv>

We highly recommend that you update SSL certificates with:
    pip install -U "urllib3[secure]" certifi

Details: https://app.datarobot.com/docs/predictions/batch/batch-prediction-api/index.html
"""
import argparse
import contextlib
import json
import logging
import os
import sys
import time
import threading
import ssl

try:
    from urllib2 import urlopen, HTTPError, Request
except ImportError:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError


API_KEY = 'NjMyYzg0Zjg4YmY5MDc5MmViMWIwOGNiOmxwbzFzeFpQcUZUcm5Ca0V5OEVZZHc3Mkc3aXhJY1pjaklwL2xRQXNCSkk9'
BATCH_PREDICTIONS_URL = 'https://app2.datarobot.com/api/v2/batchPredictions/'
DEPLOYMENT_ID = '632e178cdcbb5d1d5e3d6942'
POLL_INTERVAL = 15
CHUNK = 64 * 1024

logs_counter = 0


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
        'input_file', type=argparse.FileType('rb'), help='Input CSV file with data to be scored.'
    )
    parser.add_argument(
        'output_file', type=argparse.FileType('wb'), help='Output CSV file with the scored data.'
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
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        dest="timeout",
        help="Set the timeout value in seconds for the up- and download connections "
             "(default: 600 seconds, meaning 10 minutes)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    input_file = args.input_file
    output_file = args.output_file
    ssl_insecure = args.ssl_insecure
    timeout = args.timeout

    payload = {
        'deploymentId': DEPLOYMENT_ID,
        'includePredictionStatus': True,
        # If explanations are required, uncomment the line below
        # 'maxExplanations': 3,
        # 'thresholdHigh': 0.5,
        # 'thresholdLow': 0.15,
        # For multiclass explanations only one of the 2 fields below may be specified
        # Explain this number of top predicted classes in each row
        # 'explanationNumTopClasses': 1,
        # Explain this list of class names
        # 'explanationClassNames': [],
        # Uncomment this for Prediction Warnings, if enabled for your deployment.
        # 'predictionWarningEnabled': True,
    }

    try:
        make_datarobot_batch_predictions(input_file, output_file, payload, ssl_insecure, timeout)
    except DataRobotPredictionError as err:
        logger.error('Error: %s', err)
        return 1

    return 0


def make_datarobot_batch_predictions(
        input_file,
        output_file,
        payload,
        ssl_insecure=False,
        timeout=None
):
    # Create new job for batch predictions
    job = _request(
        'POST',
        BATCH_PREDICTIONS_URL,
        data=payload,
        ssl_insecure=ssl_insecure,
        timeout=timeout,
    )
    links = job['links']

    logger.info(
        'Created Batch Prediction job ID {job_id} for deployment ID {deployment_id}'
        ' ({intake} -> {output}) on {self_link}.'.format(
            job_id=job['id'],
            deployment_id=DEPLOYMENT_ID,
            intake=job['jobSpec']['intakeSettings']['type'],
            output=job['jobSpec']['outputSettings']['type'],
            self_link=links['self'],
        )
    )

    # Simultaneously upload
    upload_stream = threading.Thread(
        target=upload_datarobot_batch_predictions,
        args=(job, input_file, ssl_insecure, timeout),
    )
    upload_stream.daemon = True
    upload_stream.start()

    # Simultaneously download
    download_stream = threading.Thread(
        target=download_datarobot_batch_predictions,
        args=(job, output_file, ssl_insecure, timeout),
    )
    download_stream.daemon = True
    download_stream.start()

    # Wait until job's complete
    job_url = links['self']
    while True:
        try:
            job = _request('GET', job_url, ssl_insecure=ssl_insecure, timeout=timeout)
            status = job['status']
            if status == JobStatus.INITIALIZING:
                queue_position = job.get("queuePosition")

                if queue_position is None:
                    logger.info("Waiting for other jobs to complete")
                elif queue_position > 0:
                    logger.info(
                        "Waiting for other jobs to complete: {}".format(queue_position)
                    )
                else:
                    logger.debug("No queuePosition yet. Waiting for one..")

                _check_logs(job)
                time.sleep(POLL_INTERVAL)
                continue

            elif status == JobStatus.RUNNING:
                logger.info(
                    "Waiting for the job to complete: {}%".format(
                        round(float(job["percentageCompleted"]))
                    )
                )

                logger.info('Number of scored rows: {}'.format(job['scoredRows']))
                logger.info('Number of failed rows: {}'.format(job['failedRows']))
                logger.info('Number of skipped rows: {}'.format(job['skippedRows']))

                _check_logs(job)
                time.sleep(POLL_INTERVAL)
                continue

            elif status in [JobStatus.COMPLETED, JobStatus.ABORTED]:
                upload_stream.join()
                download_stream.join()

            _check_logs(job)
            return

        except KeyboardInterrupt:
            print(
                "KeyboardInterrupt detected, aborting job. "
                "Hang on for a few seconds while we clean up..."
            )
            try:
                _request(
                    "DELETE",
                    BATCH_PREDICTIONS_URL
                    + "{id}/".format(id=job["id"]),
                    to_json=False,
                    ssl_insecure=ssl_insecure,
                    timeout=timeout,
                    )
            # It is possible to fail a deletion if the job was COMPLETED before the client
            # registered it. In that case just ignore it.
            except Exception:
                pass
            return

        except Exception as e:
            if 'status' in job and not isinstance(e, DataRobotPredictionError):
                logger.exception('Unexpected error occurred')
                raise DataRobotPredictionError(
                    'An unexpected error occurred.\n\n'
                    '{err_type}: {err_msg}\n\n'
                    'Job {job_id} is {job_status}\n'
                    '{job_details}.\nLog: {job_logs}'.format(
                        err_type=type(e).__name__,
                        err_msg=e,
                        job_id=job['id'],
                        job_status=job['status'],
                        job_details=job['statusDetails'],
                        job_logs=job['logs'],
                    )
                )

            else:
                raise e


def upload_datarobot_batch_predictions(job_spec, input_file, ssl_insecure, timeout):
    logger.info('Start uploading csv data')

    upload_url = job_spec['links']['csvUpload']
    headers = {
        'Content-length': os.path.getsize(input_file.name),
        'Content-type': 'text/csv; encoding=utf-8',
    }
    try:
        _request(
            'PUT',
            upload_url,
            data=input_file,
            headers=headers,
            to_json=False,
            ssl_insecure=ssl_insecure,
            timeout=timeout,
        )

    except DataRobotPredictionError as err:
        logger.error('Error, attempting to abort the job and exit: %s', err)
        _request(
            "DELETE",
            BATCH_PREDICTIONS_URL
            + "{id}/".format(id=job_spec["id"]),
            to_json=False,
            ssl_insecure=ssl_insecure,
            timeout=timeout,
            )

    logger.info('Uploading is finished')


def download_datarobot_batch_predictions(job_spec, output_file, ssl_insecure, timeout):
    logger.info('Start downloading csv data')

    job_url = job_spec['links']['self']
    job_status = job_spec['status']

    while job_status not in JobStatus.DOWNLOADABLE:
        job_spec = _request('GET', job_url, ssl_insecure=ssl_insecure, timeout=timeout)
        job_status = job_spec['status']
        time.sleep(1)

    download_url = job_spec['links']['download']
    try:
        with contextlib.closing(
                _request(
                    'GET',
                    download_url,
                    to_json=False,
                    ssl_insecure=ssl_insecure,
                    timeout=timeout
                )
        ) as response:
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                output_file.write(chunk)

    except DataRobotPredictionError as err:
        logger.error('Error, attempting to abort the job and exit: %s', err)
        _request(
            "DELETE",
            BATCH_PREDICTIONS_URL
            + "{id}/".format(id=job_spec["id"]),
            to_json=False,
            ssl_insecure=ssl_insecure,
            timeout=timeout,
            )

    logger.info("Waiting for the job to complete: 100%")
    logger.info('Results downloaded to: {}'.format(output_file.name))


def _request(method, url, data=None, headers=None, to_json=True, ssl_insecure=False, timeout=None):
    headers = _prepare_headers(headers)

    if isinstance(data, dict):
        data = json.dumps(data).encode('utf-8')  # for python3
        headers.update({'Content-Type': 'application/json; encoding=utf-8'})

    ctx = ssl.create_default_context()
    if ssl_insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    request = Request(url, headers=headers, data=data)
    request.get_method = lambda: method
    try:
        response = urlopen(request, context=ctx, timeout=timeout)
        if to_json:
            result = response.read()
            response.close()

            # json.loads() in 2.7 and prior to 3.6 needed strings, not bytes:
            # https://docs.python.org/3/whatsnew/3.6.html#json.
            if sys.version_info < (3, 6):
                result = result.decode('utf-8')

            return json.loads(result)

        return response

    except HTTPError as e:
        err_msg = '{code} Error: {msg}'.format(code=e.code, msg=e.read())
        raise DataRobotPredictionError(err_msg)

    except Exception as e:
        err_msg = 'Unhandled exception: {e}'.format(e=e)
        raise DataRobotPredictionError(err_msg)


def _prepare_headers(headers=None):
    if not headers:
        headers = {}
    headers.update({
        'Authorization': 'Bearer {}'.format(API_KEY),
        'User-Agent': 'IntegrationSnippet-Requests',
    })
    return headers


def _check_logs(job):
    global logs_counter
    logs = job['logs']
    if len(logs) > logs_counter:
        new_logs = logs[logs_counter:]
        for log in new_logs:
            logger.info(log)
            logs_counter += 1


class DataRobotPredictionError(Exception):
    """Raised if there are issues getting predictions from DataRobot"""


class JobStatus(object):
    INITIALIZING = 'INITIALIZING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    ABORTED = 'ABORTED'

    DOWNLOADABLE = [RUNNING, COMPLETED, ABORTED]


if __name__ == '__main__':
    sys.exit(main())

