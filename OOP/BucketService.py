from urllib.parse import urlparse
import boto3

class BucketService:
    @staticmethod
    def addToBucket(file_obj, file_path_url):
        # Extract key from full URL
        parsed_url = urlparse(file_path_url)
        s3_key = parsed_url.path.lstrip('/')  # remove leading slash
        bucket = parsed_url.netloc.split('.')[0]  # vesilebucket from 'vesilebucket.s3.amazonaws.com'

        s3 = boto3.client('s3')
        s3.upload_fileobj(file_obj, bucket, s3_key)
        print(f"Uploaded to: https://{bucket}.s3.amazonaws.com/{s3_key}")

    
    @staticmethod
    def removeFromBucket(filePath):
        #bucket will take the path and remove it from s3 bucket
        return
