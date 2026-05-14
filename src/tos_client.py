import tos
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TOSClient:
    def __init__(self,access_key,secret_key,endpoint,region,bucket_name):
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint
        self.region = region
        self.bucket_name = bucket_name
        self.Client = self.InitClient()
    
    def InitClient(self):
        return tos.TosClientV2(self.access_key, self.secret_key, self.endpoint, self.region)
    
    def UploadFile(self,file_path,tos_prefix=""):
        try:
            if not os.path.isdir(file_path):
                raise Exception("file_path is not a directory")
            if tos_prefix and not tos_prefix.endswith('/'):
                tos_prefix += '/'
            for root, dirs, files in os.walk(file_path):
                for file in files:
                    local_path = os.path.join(root, file)
                    real_path = os.path.relpath(local_path, file_path)
                    tos_key = tos_prefix + real_path
                    self.Client.put_object_from_file(self.bucket_name, tos_key, local_path)
                    logging.info(f"上传文件成功: {tos_key}")
        except Exception as e:
            logging.error(f"上传文件失败: {e}")