
"""
Usage:
    python datarobot_predict.py <input-file.csv>

This example uses the requests library which you can install with:
    pip install requests
We highly recommend that you update SSL certificates with:
    pip install -U "urllib3[secure]" certifi
"""
import sys
import requests

API_URL = 'https://app2.datarobot.com/api/v2/deployments/{deployment_id}/predictions/'
API_KEY = 'NjMyYzg0Zjg4YmY5MDc5MmViMWIwOGNiOmxwbzFzeFpQcUZUcm5Ca0V5OEVZZHc3Mkc3aXhJY1pjaklwL2xRQXNCSkk9'

DEPLOYMENT_ID = '6329929cd452ce5ad78adfe7'

# Don't change this. It is enforced server-side too.
MAX_PREDICTION_FILE_SIZE_BYTES = 52428800  # 50 MB


class DataRobotPredictionError(Exception):
    """Raised if there are issues getting predictions from DataRobot"""


def make_datarobot_deployment_predictions(data, deployment_id):
    """
    Make predictions on data provided using DataRobot deployment_id provided.
    See docs for details:
         https://app2.datarobot.com/docs/predictions/api/dr-predapi.html

    Parameters
    ----------
    data : str
        If using CSV as input:
        Feature1,Feature2
        numeric_value,string

        Or if using JSON as input:
        [{"Feature1":numeric_value,"Feature2":"string"}]

    deployment_id : str
        The ID of the deployment to make predictions with.

    Returns
    -------
    Response schema:
        https://app2.datarobot.com/docs/predictions/api/dr-predapi.html#response-schema

    Raises
    ------
    DataRobotPredictionError if there are issues getting predictions from DataRobot
    """
    # Set HTTP headers. The charset should match the contents of the file.
    headers = {
        # As default, we expect CSV as input data.
        # Should you wish to supply JSON instead,
        # comment out the line below and use the line after that instead:
        'Content-Type': 'text/plain; charset=UTF-8',
        # 'Content-Type': 'application/json; charset=UTF-8',

        'Authorization': 'Bearer {}'.format(API_KEY),
    }

    url = API_URL.format(deployment_id=deployment_id)

    # Prediction Explanations:
    # See the documentation for more information:
    # https://app2.datarobot.com/docs/predictions/api/dr-predapi.html#request-pred-explanations
    # Should you wish to include Prediction Explanations or Prediction Warnings in the result,
    # Change the parameters below accordingly, and remove the comment from the params field below:

    params = {
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
        # 'predictionWarningEnabled': 'true',
    }
    # Make API request for predictions
    predictions_response = requests.post(
        url,
        data=data.encode(encoding='utf-8'),
        headers=headers,
        # Prediction Explanations:
        # Uncomment this to include explanations in your prediction
        # params=params,
    )
    _raise_dataroboterror_for_status(predictions_response)
    # Return a Python dict following the schema in the documentation
    return predictions_response.json()


def _raise_dataroboterror_for_status(response):
    """Raise DataRobotPredictionError if the request fails along with the response returned"""
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        err_msg = '{code} Error: {msg}'.format(
            code=response.status_code, msg=response.text)
        raise DataRobotPredictionError(err_msg)


def main(file, deployment_id):
    """
    Return an exit code on script completion or error. Codes > 0 are errors to the shell.
    Also useful as a usage demonstration of
    `make_datarobot_deployment_predictions(data, deployment_id)`
    """
    if len(file) == 0:
        print(
            'Input file is required argument. '
            'Usage: python datarobot_predict.py <input-file.csv>')
        return 1
    data = file
    data_size = sys.getsizeof(data)
    if data_size >= MAX_PREDICTION_FILE_SIZE_BYTES:
        print((
                  'Input file is too large: {} bytes. '
                  'Max allowed size is: {} bytes.'
              ).format(data_size, MAX_PREDICTION_FILE_SIZE_BYTES))
        return 1
    try:
        predictions = make_datarobot_deployment_predictions(data, deployment_id)
    except DataRobotPredictionError as exc:
        print(exc)
        return 1

    return predictions

