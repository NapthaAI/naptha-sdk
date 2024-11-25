import ipfshttpclient
import json
import os
import uuid
import shutil
import re
import zipfile
from urllib.parse import urlparse
from pathlib import Path

def validate_and_format_gateway_url(url):
    """
    Validate and format IPFS gateway URL to the required format: /dns/host/tcp/port/http
    """
    if url is None:
        raise ValueError("IPFS gateway URL is not provided")
    
    # If already in correct format, validate and return
    if url.startswith('/dns/') or url.startswith('/ip4/') or url.startswith('/ip6/'):
        # Basic validation for the correct format
        parts = url.split('/')
        if len(parts) < 6 or 'tcp' not in parts or 'http' not in parts:
            raise ValueError(f"Invalid IPFS gateway URL format: {url}")
        return url

    # Handle http(s):// format
    if url.startswith(('http://', 'https://')):
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (80 if parsed.scheme == 'http' else 443)
        return f"/dns/{host}/tcp/{port}/http"

    # Handle host:port format
    if ':' in url:
        host, port = url.split(':')
        try:
            port = int(port)
        except ValueError:
            raise ValueError(f"Invalid port number in URL: {url}")
        return f"/dns/{host}/tcp/{port}/http"

    # Handle IP address format
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, url):
        return f"/ip4/{url}/tcp/5001/http"

    # If just hostname is provided, assume default port
    return f"/dns/{url}/tcp/5001/http"

DEFAULT_IPFS_GATEWAY = validate_and_format_gateway_url(os.getenv("IPFS_GATEWAY_URL", None))
DEFAULT_OUTPUT_DIR = os.getenv("BASE_OUTPUT_DIR", None)

if DEFAULT_OUTPUT_DIR is None:
    raise ValueError("BASE_OUTPUT_DIR is not set")

class IPFSClient:
    def __init__(self, ipfs_gateway_url=DEFAULT_IPFS_GATEWAY):
        """
        Initialize IPFS client with a gateway URL
        Args:
            ipfs_gateway_url: IPFS gateway URL in any supported format
        """
        self.gateway_url = validate_and_format_gateway_url(ipfs_gateway_url)
        self.client = ipfshttpclient.connect(self.gateway_url)

    def get_gateway_url(self):
        """
        Return the formatted gateway URL being used
        """
        return self.gateway_url

    def push_json(self, data):
        """
        Push JSON data to IPFS and pin it
        Returns: IPFS hash of the stored data
        """
        json_str = json.dumps(data)
        ipfs_hash = self.client.add_json(data)
        self.pin_hash(ipfs_hash)
        return ipfs_hash

    def get_json(self, ipfs_hash):
        """
        Retrieve JSON data from IPFS using its hash
        Returns: Decoded JSON data
        """
        return self.client.get_json(ipfs_hash)

    def upload_folder(self, folder_path, zip_folder=False):
        """
        Upload an entire folder to IPFS and pin it
        Args:
            folder_path: Path to the folder to upload
            zip_folder: If True, zip the folder before uploading
        Returns: IPFS hash of the folder
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder {folder_path} does not exist")
        
        upload_path = folder_path
        temp_zip_path = None
        
        try:
            if zip_folder:
                # Create a temporary zip file
                temp_zip_path = f"{folder_path}_{uuid.uuid4()}"
                shutil.make_archive(temp_zip_path, 'zip', folder_path)
                upload_path = f"{temp_zip_path}.zip"
                
            result = self.client.add(upload_path, recursive=True)
            
            # Handle both single file and directory results
            if isinstance(result, list):
                ipfs_hash = result[-1]['Hash']
            else:
                ipfs_hash = result['Hash']
                
            # Pin the content
            self.pin_hash(ipfs_hash)
            return ipfs_hash
            
        finally:
            # Clean up zip file if created
            if temp_zip_path and os.path.exists(f"{temp_zip_path}.zip"):
                os.remove(f"{temp_zip_path}.zip")

    def download_folder(self, ipfs_hash, output_path=None):
        """
        Download a folder from IPFS using its hash
        Args:
            ipfs_hash: IPFS hash of the folder to download
            output_path: Path where to download the folder. If None, creates a UUID directory under DEFAULT_OUTPUT_DIR
        Returns:
            Path where the folder was downloaded
        """
        if output_path is None:
            output_path = os.path.join(DEFAULT_OUTPUT_DIR, str(uuid.uuid4()))

        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        # Create a temporary directory for the initial download
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download to temp directory first
            self.client.get(ipfs_hash, target=temp_dir)
            
            # Find the downloaded content
            hash_path = os.path.join(temp_dir, ipfs_hash)
            
            # Check if it's a directory or a file
            if os.path.isdir(hash_path):
                # If it's a directory, move its contents
                for item in os.listdir(hash_path):
                    source = os.path.join(hash_path, item)
                    dest = os.path.join(output_path, item)
                    if os.path.exists(dest):
                        if os.path.isdir(dest):
                            shutil.rmtree(dest)
                        else:
                            os.remove(dest)
                    shutil.move(source, dest)
            else:
                # If it's a file (like a zip file), just move it
                filename = f"downloaded{os.path.splitext(hash_path)[1]}"
                if not filename.endswith('.zip'):
                    filename += '.zip'
                dest = os.path.join(output_path, filename)
                shutil.move(hash_path, dest)
                
                # If it's a zip file, extract it
                if zipfile.is_zipfile(dest):
                    with zipfile.ZipFile(dest, 'r') as zip_ref:
                        zip_ref.extractall(output_path)
                    # Remove the zip file after extraction
                    os.remove(dest)

        return output_path

    def upload_file(self, file_path):
        """
        Upload a single file to IPFS and pin it
        Args:
            file_path: Path to the file to upload
        Returns:
            IPFS hash of the uploaded file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} does not exist")
        
        if not os.path.isfile(file_path):
            raise ValueError(f"{file_path} is not a file")

        try:
            result = self.client.add(file_path)
            ipfs_hash = result['Hash']
            # Pin the content
            self.pin_hash(ipfs_hash)
            return ipfs_hash
        except Exception as e:
            raise Exception(f"Failed to upload file {file_path}: {str(e)}")

    def download_file(self, ipfs_hash, output_path=None):
        """
        Download a single file from IPFS using its hash
        Args:
            ipfs_hash: IPFS hash of the file to download
            output_path: Path where to save the file. If None, creates a UUID directory under DEFAULT_OUTPUT_DIR
        Returns:
            Path where the file was downloaded
        """
        if output_path is None:
            # Create a UUID directory and use a default filename
            output_dir = os.path.join(DEFAULT_OUTPUT_DIR, str(uuid.uuid4()))
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, 'downloaded_file')

        # Ensure the parent directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            # Create a temporary directory for downloading
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download to temp directory
                self.client.get(ipfs_hash, target=temp_dir)
                
                # Find the downloaded content
                hash_dir = os.path.join(temp_dir, ipfs_hash)
                
                if os.path.isdir(hash_dir):
                    # If it's a directory, get the first file
                    files = os.listdir(hash_dir)
                    if files:
                        source = os.path.join(hash_dir, files[0])
                        shutil.copy2(source, output_path)
                else:
                    # If it's a file, move it directly
                    shutil.copy2(hash_dir, output_path)

            return output_path
        except Exception as e:
            raise Exception(f"Failed to download file with hash {ipfs_hash}: {str(e)}")
    
    def pin_hash(self, ipfs_hash):
        """
        Pin content to ensure it's not garbage collected
        """
        return self.client.pin.add(ipfs_hash)

    def unpin_hash(self, ipfs_hash):
        """
        Unpin content when no longer needed
        """
        return self.client.pin.rm(ipfs_hash)

    def get_file_size(self, ipfs_hash):
        """
        Get the size of content stored at hash
        """
        return self.client.files.stat(f'/ipfs/{ipfs_hash}')['Size']

    def close(self):
        """
        Close the IPFS client connection
        """
        self.client.close()


if __name__ == "__main__":
    import os
    import tempfile
    import logging
    import time
    from datetime import datetime

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def run_test(test_func):
        try:
            test_func()
            logger.info(f"✅ {test_func.__name__} passed")
        except Exception as e:
            logger.error(f"❌ {test_func.__name__} failed: {str(e)}")
            raise

    def test_gateway_url_formats():
        """Test different gateway URL formats"""
        test_cases = [
            "/dns/provider.akash.pro/tcp/31832/http",
            "http://provider.akash.pro:31832",
            "provider.akash.pro:31832",
        ]
        
        for url in test_cases:
            client = IPFSClient(url)
            formatted_url = client.get_gateway_url()
            logger.info(f"Original: {url} -> Formatted: {formatted_url}")
            client.close()

    def test_json_operations():
        """Test JSON push and retrieve operations"""
        client = IPFSClient()
        
        # Test simple JSON
        simple_data = {"test": "value", "timestamp": str(datetime.now())}
        simple_hash = client.push_json(simple_data)
        retrieved_simple = client.get_json(simple_hash)
        assert retrieved_simple == simple_data
        
        # Test nested JSON
        nested_data = {
            "level1": {
                "level2": {
                    "level3": ["a", "b", "c"],
                    "timestamp": str(datetime.now())
                }
            }
        }
        nested_hash = client.push_json(nested_data)
        retrieved_nested = client.get_json(nested_hash)
        assert retrieved_nested == nested_data
        
        # Test array JSON
        array_data = [1, 2, {"key": "value"}, [4, 5, 6]]
        array_hash = client.push_json(array_data)
        retrieved_array = client.get_json(array_hash)
        assert retrieved_array == array_data
        
        client.close()

    def test_folder_operations():
        """Test folder upload and download operations"""
        client = IPFSClient()
        
        # Create test folder structure
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Created temporary directory: {temp_dir}")
            
            # Create test files
            test_files = {
                "file1.txt": "Hello World",
                "file2.json": '{"key": "value"}',
                "subfolder/file3.txt": "Nested file content",
            }
            
            # Create and verify input files
            for file_path, content in test_files.items():
                full_path = os.path.join(temp_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)
                logger.info(f"Created test file: {full_path}")
            
            try:
                # Test regular folder upload
                folder_hash = client.upload_folder(temp_dir)
                logger.info(f"Folder uploaded with hash: {folder_hash}")
                
                # Test folder download
                download_path = client.download_folder(folder_hash)
                logger.info(f"Folder downloaded to: {download_path}")
                
                # Verify downloaded files
                logger.info(f"Looking for files in download directory: {download_path}")
                
                for file_path, expected_content in test_files.items():
                    downloaded_file = os.path.join(download_path, file_path)
                    logger.info(f"Checking file: {downloaded_file}")
                    
                    assert os.path.exists(downloaded_file), f"File not found: {downloaded_file}"
                    with open(downloaded_file, 'r') as f:
                        actual_content = f.read()
                        assert actual_content == expected_content, (
                            f"Content mismatch for {file_path}. "
                            f"Expected: {expected_content}, Got: {actual_content}"
                        )
                    logger.info(f"Successfully verified file: {downloaded_file}")
                
                # Test zipped folder upload
                logger.info("Testing zipped folder upload...")
                zip_hash = client.upload_folder(temp_dir, zip_folder=True)
                logger.info(f"Zipped folder uploaded with hash: {zip_hash}")
                
                # Download and verify zipped folder
                zip_download_path = client.download_folder(zip_hash)
                logger.info(f"Zipped folder downloaded and extracted to: {zip_download_path}")
                
                # Verify the extracted files
                logger.info(f"Verifying extracted files in: {zip_download_path}")
                base_name = os.path.basename(temp_dir)
                for file_path, expected_content in test_files.items():
                    # The files will be inside a directory named after the original folder
                    extracted_file = os.path.join(zip_download_path, file_path)
                    logger.info(f"Checking extracted file: {extracted_file}")
                    
                    assert os.path.exists(extracted_file), f"Extracted file not found: {extracted_file}"
                    with open(extracted_file, 'r') as f:
                        actual_content = f.read()
                        assert actual_content == expected_content, (
                            f"Content mismatch for extracted file {file_path}. "
                            f"Expected: {expected_content}, Got: {actual_content}"
                        )
                    logger.info(f"Successfully verified extracted file: {extracted_file}")
                
                # Get and verify file sizes
                regular_size = client.get_file_size(folder_hash)
                zip_size = client.get_file_size(zip_hash)
                logger.info(f"Regular size: {regular_size}, Zip size: {zip_size}")
                
            except Exception as e:
                logger.error(f"Test failed with error: {str(e)}")
                logger.error(f"Download path: {download_path}")
                logger.error("Directory contents:")
                for root, dirs, files in os.walk(download_path):
                    logger.error(f"  Directory: {root}")
                    for d in dirs:
                        logger.error(f"    Subdirectory: {d}")
                    for f in files:
                        logger.error(f"    File: {f}")
                raise
            
        client.close()

    def test_file_operations():
        """Test file upload and download operations"""
        client = IPFSClient()
        
        try:
            # Create a test file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
                content = "Hello, this is a test file content!"
                temp_file.write(content)
                file_path = temp_file.name
            
            logger.info(f"Created test file: {file_path}")
            
            # Test file upload
            file_hash = client.upload_file(file_path)
            logger.info(f"File uploaded with hash: {file_hash}")
            
            # Test file download with auto-generated path
            auto_download_path = client.download_file(file_hash)
            logger.info(f"File downloaded to: {auto_download_path}")
            
            # Verify content
            with open(auto_download_path, 'r') as f:
                downloaded_content = f.read()
            assert downloaded_content == content, (
                f"Content mismatch. Expected: {content}, Got: {downloaded_content}"
            )
            logger.info("Successfully verified auto-generated path download")
            
            # Test file download with specified path
            specified_path = os.path.join(DEFAULT_OUTPUT_DIR, 'test_output', 'specified_test_file.txt')
            specified_download_path = client.download_file(file_hash, specified_path)
            logger.info(f"File downloaded to specified path: {specified_download_path}")
            
            # Verify content of specified path download
            with open(specified_download_path, 'r') as f:
                specified_content = f.read()
            assert specified_content == content, (
                f"Content mismatch in specified path. Expected: {content}, Got: {specified_content}"
            )
            logger.info("Successfully verified specified path download")
            
            # Clean up
            os.remove(file_path)
            os.remove(auto_download_path)
            os.remove(specified_download_path)
            
        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            raise
        finally:
            client.close()

    def test_pin_operations():
        """Test pin and unpin operations"""
        client = IPFSClient()
        
        # Create and pin some test data
        test_data = {"pin_test": "data"}
        hash_value = client.push_json(test_data)  # Should auto-pin
        
        # Verify it's pinned
        pin_list = client.client.pin.ls()
        assert hash_value in str(pin_list)
        
        # Unpin
        client.unpin_hash(hash_value)
        
        # Verify it's unpinned
        pin_list = client.client.pin.ls()
        assert hash_value not in str(pin_list)
        
        # Pin again
        client.pin_hash(hash_value)
        
        # Verify it's pinned again
        pin_list = client.client.pin.ls()
        assert hash_value in str(pin_list)
        
        client.close()

    def test_error_handling():
        """Test error handling scenarios"""
        client = IPFSClient()
        
        # Test invalid IPFS hash
        try:
            client.get_json("invalid_hash")
            assert False, "Should have raised an error"
        except Exception as e:
            logger.info(f"Expected error caught: {str(e)}")
        
        # Test non-existent folder
        try:
            client.upload_folder("/path/that/does/not/exist")
            assert False, "Should have raised an error"
        except FileNotFoundError as e:
            logger.info(f"Expected error caught: {str(e)}")
        
        client.close()

    # Run all tests
    logger.info("Starting IPFS Client tests...")
    
    run_test(test_gateway_url_formats)
    run_test(test_json_operations)
    run_test(test_folder_operations)
    run_test(test_file_operations)
    run_test(test_pin_operations)
    run_test(test_error_handling)
    
    logger.info("All tests completed!")