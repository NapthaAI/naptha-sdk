import requests
import tempfile
import tarfile
import os
from pathlib import Path

def test():
    url = 'http://54.82.77.109:7001/GetStorage/gqcrjmahcxapbcvpy6gx'
    # /home/ubuntu/node/node/storage/fs/gqcrjmahcxapbcvpy6gx
    response = requests.get(url)
    response.raise_for_status()
    print(response.status_code)

    temp_file_name = None
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp_file:
        tmp_file.write(response.content)
        temp_file_name = tmp_file.name

    # Ensure output directory exists
    output_path = Path('./output')
    output_path.mkdir(parents=True, exist_ok=True)

    # Extract the tar.gz file
    with tarfile.open(temp_file_name, "r:gz") as tar:
        tar.extractall(path='./output')

    
    # Cleanup temporary file
    Path(temp_file_name).unlink(missing_ok=True)

if __name__ == '__main__':
    test()