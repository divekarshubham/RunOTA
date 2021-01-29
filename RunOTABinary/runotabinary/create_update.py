import boto3
import os
import time
from runotabinary.configs.config_project import OtaProject
from runotabinary.logger import logger
from uuid import uuid4


class CreateUpdate:
    def __init__(self, fileNameInUpload, fileToUpload):
        self._awsIotClient = boto3.client('iot')
        self.project = OtaProject()
        self._s3Bucket = AWSS3Bucket(self.project.s3_bucket_name)
        self.filename = fileNameInUpload
        self.filepath = fileToUpload

    def clear_pending_jobs(self):
        '''
        For current thing, check if there is any pending jobs.
        Remove all pending jobs.
        '''
        try:
            response_queued = {}
            response_inprogress = {}
            response_queued = self._awsIotClient.list_job_executions_for_thing(thingName=self.project.thing_name,
                                                                        status='QUEUED')
            response_inprogress = self._awsIotClient.list_job_executions_for_thing(thingName=self.project.thing_name,
                                                                                    status='IN_PROGRESS')

        except Exception as e:
            logger.warning(f"aws iot list_job_executions_for_thing failed. Err: {e}")

        pending_jobs = response_queued["executionSummaries"] + response_inprogress["executionSummaries"]
        for job in pending_jobs:
            logger.debug(f'Clear pending job: {job["jobId"]}')
            self.cancel_job(job["jobId"].split("AFR_OTA-")[1])

    def cancel_job(self, jobId):
        """
        Cancel the input job ID.
        :param jobId(str): The AWS IoT job ID to cancel.
        """
        response = {}
        try:
            response = self._awsIotClient.cancel_job(jobId=f'AFR_OTA-{jobId}', comment='OTA integration testing cancellation of incomplete job.', force=True)
            logger.info(f'AFR_OTA-{jobId} job cancelled')
        except Exception as e:
            logger.error("Unable to cancel job with ID: " + jobId)
            logger.error(f"Response: {response}, Exception: {e}")
    
    def upload_firmware_to_s3_bucket(self, localPathToFirmware, firmwareFileName):
        """
        Upload a firmware image to the unsigned S3 bucket associated with this OTA agent.
        :param localPathToFirmware(str): The path on the machine this script is running of the firmware image.
        :param firmwareFileName(str): The name of the firmware, this is used as the key in the S3 bucket.
        """
        logger.info('Uploading firmware to S3')
        self._s3Bucket.upload_file(localPathToFirmware, firmwareFileName)
    
    def create_update(self, protocols, deployment_files, role_arn=None, url_expired=3600):
        """
        Create an OTA update job.
        Returns the AWS IoT OTA Update ID.
        :param deviceImageFileName(str): The full path to the image in the device's file system. For devices not using
                a file system any string can be put in here.
        :param streamId (str): The AWS ID of the stream returned from AwsOtaAgent.create_iot_stream().
        :param signerJobId(str): The AWS Job ID of the completed AWS Signer operation. This ID was returned from
                function AwsOtaAgent.sign_firmware_in_s3_bucket().
        :param deploymentFiles (dict):  An AWS CLI compliant dictionary of the deployment file(s)
                                        information to create an OTA update job for.
        """

        # Timeout for the AWS Job service to create an OTA update job.
        AWS_CREATE_OTA_UPDATE_JOB_TIMEOUT = 60
        create_ota_response = {}
        
        create_ota_response = self._awsIotClient.create_ota_update(
            otaUpdateId=str(uuid4()),
            targets=[
                self.project.thing_arn
            ],
            targetSelection='SNAPSHOT',
            roleArn=self.project.ota_update_role_arn,
            files=deployment_files,
            protocols=protocols,
            awsJobPresignedUrlConfig={
                'expiresInSec': url_expired
            }
        )

        # Confirm that the OTA update job is ready.
        timeout_end = time.perf_counter() + AWS_CREATE_OTA_UPDATE_JOB_TIMEOUT
        ota_create_in_progress = True
        ota_update_info = None
        while ota_create_in_progress and time.perf_counter() < timeout_end:
            time.sleep(1)
            otaGetStatusResponse = {}
            otaGetStatusResponse = self._awsIotClient.get_ota_update(
                otaUpdateId = create_ota_response.get('otaUpdateId'))
            ota_update_info = otaGetStatusResponse.get('otaUpdateInfo')

            if ota_update_info.get('otaUpdateStatus') in ('CREATE_COMPLETE', 'CREATE_FAILED'):
                ota_create_in_progress = False

        if ota_create_in_progress == True:
            logger.error(f"Error: OTA update creation timed out for OTA update ID {ota_update_info.get('otaUpdateId')}")
            return None

        # Check for errors and show us what those errors might be.
        if ota_update_info.get('otaUpdateStatus') != 'CREATE_COMPLETE':
            logger.error(f"OTA update creation failed for OTA update ID {ota_update_info.get('otaUpdateId')}")
            if ('errorInfo' in ota_update_info):
                logger.error(f"Code: {ota_update_info.get('errorInfo').get('code')}")
                logger.error(f"Details: {ota_update_info.get('errorInfo').get('message')}")
        else:
            logger.info(f"Created OTA Update ID {ota_update_info.get('otaUpdateId')} (AWS IoT job ID = {ota_update_info.get('awsIotJobId')}).")

        return ota_update_info.get('otaUpdateId')

    def create_ota_update(self, urlExpired=3600):
        """Create an OTA update in AWS IoT by using the otaConfig.
        We follow the path of:
            1. Upload unsigned image to the unsigned s3 bucket.
            2. Sign the image in the unsigned s3 bucket to the signed s3 bucket.
            3. Create a IoT stream from the image in the signed s3 bucket.
            4. Create an OTA Update job from the IoT Stream and signer information.
        This function follows the happy path OTA case. It is nice for testing changes
        where the only image is manipulated.
        Returns AWS IoT Ota Update ID
        Args:
            otaConfig - 'ota_config' from board.json
        """
        # Upload to the s3 bucket.
        self.upload_firmware_to_s3_bucket(
            self.filepath,
            self.filename
        )

        signingProfile = f'{self.project.thing_name[-8:]}_linux'
        otaUpdateId = self.create_update(
            protocols=[self.project.data_protocol],
            url_expired=urlExpired,
            deployment_files=[
                {
                    'fileName': self.filename,
                    'fileVersion': '1',
                    'fileLocation': {
                        's3Location': {
                            'bucket': self.project.s3_bucket_name,
                            'key': os.path.basename(self.filepath),
                            'version': self._s3Bucket.get_s3_object(os.path.basename(self.filepath)).version_id
                        }
                    },
                    'codeSigning': {
                        "startSigningJobParameter": {
                            'signingProfileName': signingProfile,
                            'signingProfileParameter': {
                                'platform': self.project.signer_platform,
                                'certificateArn': self.project.ecdsa_signer_certificate_arn,
                                'certificatePathOnDevice': self.project.signer_certificate_file_name
                            }
                        }
                    }
                },
            ]
        )

        return otaUpdateId


class AWSS3Bucket:
    """ AWS S3 Versioned Bucket."""
    def __init__(self, name):
        self._s3_client = boto3.resource('s3')
        self.s3_name = name
        self.s3_bucket = self._s3_client.Bucket(self.s3_name)
        self.__create_bucket()
        self.s3_keys = []

    def __create_bucket(self):
        response = None
        try:
            response = self._s3_client.meta.client.head_bucket(Bucket = self.s3_name)
        except Exception:
            self.s3_bucket = self._s3_client.create_bucket(
                Bucket = self.s3_name,
                CreateBucketConfiguration = {
                    'LocationConstraint': boto3.session.Session().region_name
                }
            )
            self._s3_client.BucketVersioning(self.s3_name).enable()

    def upload_file(self, file_path, file_name):
        self.s3_keys.append(file_name)
        self._s3_client.Bucket(self.s3_name).upload_file(file_path, file_name)

    def download_file(self, key, file_path):
        try:
            self._s3_client.Bucket(self.s3_name).download_file(key, file_path)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                logger.error("The object does not exist.")
            else:
                raise

    def get_s3_object(self, key):
        return self._s3_client.Object(self.s3_name, key)

    def cleanup(self):
        try:
            self._s3_client.meta.client.head_bucket(Bucket = self.s3_name)
        except:
            # Bucket doesn't exist nothing to clean.
            return
        for key in self.s3_keys:
            self._s3_client.Object(self.s3_name, key).delete()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

def main():
    #filename = 'ota_demo_core_mqtt2'
    #filepath = '/home/ubuntu/dev/csdk/aws-iot-device-sdk-embedded-C/build/bin/ota_demo_core_mqtt'
    #task = CreateUpdate(filename,filepath) 
    task = CreateUpdate(sys.argv[1], sys.argv[2])
    ota_update_id = task.create_ota_update()
    

if __name__ == "__main__":
    main()