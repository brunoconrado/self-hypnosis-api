"""
Storage Service - Abstraction layer for file storage
Supports local filesystem and S3-compatible storage (AWS S3, DigitalOcean Spaces)
"""

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, BinaryIO
from flask import current_app


class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    @abstractmethod
    def save(self, file_data: BinaryIO, filename: str, content_type: str) -> str:
        """Save file and return the storage path/key"""
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Delete file by path/key"""
        pass

    @abstractmethod
    def get_url(self, file_path: str) -> str:
        """Get URL to access the file"""
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if file exists"""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, file_data: BinaryIO, filename: str, content_type: str, preserve_filename: bool = False) -> str:
        """Save file to local filesystem"""
        ext = Path(filename).suffix or self._get_extension(content_type)

        if preserve_filename:
            # Use the provided filename directly (flat structure)
            safe_filename = Path(filename).name
        else:
            # Generate unique filename
            safe_filename = f"{uuid.uuid4().hex}{ext}"

        file_path = self.base_path / safe_filename

        # Write file
        with open(file_path, 'wb') as f:
            f.write(file_data.read())

        # Return just the filename
        return safe_filename

    def delete(self, file_path: str) -> bool:
        """Delete file from local filesystem"""
        full_path = self.base_path / file_path
        try:
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False

    def get_url(self, file_path: str) -> str:
        """Get URL for local file (served by Flask)"""
        return f"/api/audio/file/{file_path}"

    def exists(self, file_path: str) -> bool:
        """Check if file exists locally"""
        return (self.base_path / file_path).exists()

    def get_full_path(self, file_path: str) -> Path:
        """Get full filesystem path"""
        return self.base_path / file_path

    def _get_extension(self, content_type: str) -> str:
        """Get file extension from content type"""
        extensions = {
            'audio/webm': '.webm',
            'audio/mp4': '.m4a',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg',
        }
        return extensions.get(content_type, '.audio')


class S3StorageBackend(StorageBackend):
    """S3-compatible storage backend (AWS S3, DigitalOcean Spaces, etc.)"""

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str,
                 bucket: str, region: str):
        import boto3

        self.bucket = bucket
        self.client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

    def save(self, file_data: BinaryIO, filename: str, content_type: str, preserve_filename: bool = False) -> str:
        """Save file to S3"""
        ext = Path(filename).suffix or self._get_extension(content_type)

        if preserve_filename:
            safe_filename = Path(filename).name
        else:
            safe_filename = f"{uuid.uuid4().hex}{ext}"

        # Flat structure under audio/
        key = f"audio/{safe_filename}"

        self.client.upload_fileobj(
            file_data,
            self.bucket,
            key,
            ExtraArgs={'ContentType': content_type, 'ACL': 'public-read'}
        )

        return key

    def delete(self, file_path: str) -> bool:
        """Delete file from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=file_path)
            return True
        except Exception:
            return False

    def get_url(self, file_path: str) -> str:
        """Get public URL for S3 file"""
        # For DigitalOcean Spaces
        endpoint = self.client._endpoint.host
        return f"{endpoint}/{self.bucket}/{file_path}"

    def exists(self, file_path: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.client.head_object(Bucket=self.bucket, Key=file_path)
            return True
        except Exception:
            return False

    def _get_extension(self, content_type: str) -> str:
        """Get file extension from content type"""
        extensions = {
            'audio/webm': '.webm',
            'audio/mp4': '.m4a',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg',
        }
        return extensions.get(content_type, '.audio')


class StorageService:
    """Main storage service that uses configured backend"""

    _instance: Optional['StorageService'] = None
    _backend: Optional[StorageBackend] = None

    @classmethod
    def get_instance(cls) -> 'StorageService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def init_app(cls, app):
        """Initialize storage with Flask app config"""
        storage_type = app.config.get('STORAGE_TYPE', 'local')

        if storage_type == 's3':
            cls._backend = S3StorageBackend(
                endpoint_url=app.config['S3_ENDPOINT_URL'],
                access_key=app.config['S3_ACCESS_KEY'],
                secret_key=app.config['S3_SECRET_KEY'],
                bucket=app.config['S3_BUCKET'],
                region=app.config['S3_REGION']
            )
        else:
            cls._backend = LocalStorageBackend(
                base_path=app.config.get('STORAGE_LOCAL_PATH', './storage/audio')
            )

        cls._instance = cls()

    @property
    def backend(self) -> StorageBackend:
        if self._backend is None:
            raise RuntimeError("Storage not initialized. Call init_app first.")
        return self._backend

    def save_audio(self, file_data: BinaryIO, filename: str, content_type: str, preserve_filename: bool = False) -> str:
        """Save audio file and return storage path"""
        return self.backend.save(file_data, filename, content_type, preserve_filename)

    def delete_audio(self, file_path: str) -> bool:
        """Delete audio file"""
        return self.backend.delete(file_path)

    def get_audio_url(self, file_path: str) -> str:
        """Get URL for audio file"""
        return self.backend.get_url(file_path)

    def audio_exists(self, file_path: str) -> bool:
        """Check if audio file exists"""
        return self.backend.exists(file_path)


# Convenience function
def get_storage() -> StorageService:
    return StorageService.get_instance()
