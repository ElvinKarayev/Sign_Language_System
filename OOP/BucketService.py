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
    def removeFromBucket(file_path_url):
          # Parse URL to extract bucket name and key
        parsed_url = urlparse(file_path_url)
        s3_key = parsed_url.path.lstrip('/')
        bucket = parsed_url.netloc.split('.')[0]

        s3 = boto3.client('s3')
        try:
            s3.delete_object(Bucket=bucket, Key=s3_key)
            print(f"Deleted: https://{bucket}.s3.amazonaws.com/{s3_key}")
            return True
        except Exception as e:
            print(f"Failed to delete: {e}")
            return False
        
    @staticmethod
    def view_bucket_video(file_path_url, expiration=3600):
        """
        Generate a presigned URL for viewing an S3 video.

        :param file_path_url: Full S3 video URL
        :param expiration: URL expiration time in seconds (default: 1 hour)
        :return: Presigned URL string
        """
        parsed_url = urlparse(file_path_url)
        s3_key = parsed_url.path.lstrip('/')
        bucket = parsed_url.netloc.split('.')[0]
        

        s3 = boto3.client('s3')
        try:
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={
                    'Bucket': bucket, 
                    'Key': s3_key
                    },
                ExpiresIn=expiration
            )
            return presigned_url
        except Exception as e:
            print(f"Failed to generate presigned URL: {e}")
            return None      