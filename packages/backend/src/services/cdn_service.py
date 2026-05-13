"""
CDN Service for generating pre-signed URLs for direct image upload.
Supports Cloudflare R2 (S3-compatible) or AWS S3.
"""
import uuid
from typing import Optional, Tuple
import structlog

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    BOTO_AVAILABLE = True
except ImportError:
    BOTO_AVAILABLE = False

from src.config.database import get_settings

logger = structlog.get_logger()


class CDNService:
    """Service for managing file uploads via pre-signed URLs."""

    def __init__(self) -> None:
        settings = get_settings()
        self.provider = settings.cdn_provider
        self.bucket_name = settings.cdn_bucket_name
        self.public_url_base = settings.cdn_public_url
        self.enabled = BOTO_AVAILABLE and settings.cdn_enabled

        if self.enabled and BOTO_AVAILABLE:
            self._init_s3_client()
        else:
            self.s3_client = None
            if not BOTO_AVAILABLE:
                logger.warning("cdn.boto3_not_available", message="boto3 not installed, CDN uploads disabled")

    def _init_s3_client(self) -> None:
        """Initialize S3 client for R2 or S3."""
        settings = get_settings()
        endpoint_url = settings.cdn_endpoint_url
        access_key = settings.cdn_access_key_id
        secret_key = settings.cdn_secret_access_key
        region = settings.cdn_region

        if not all([endpoint_url, access_key, secret_key]):
            logger.warning("cdn.missing_credentials", message="CDN credentials not configured")
            self.enabled = False
            return

        config = Config(signature_version='s3v4')

        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=config
        )
        logger.info("cdn.initialized", provider=self.provider, bucket=self.bucket_name)

    def generate_upload_url(
        self,
        file_type: str = "image",
        content_type: str = "image/jpeg",
        max_size_mb: int = 5,
        vendor_id: Optional[uuid.UUID] = None
    ) -> Tuple[str, str]:
        """
        Generate a pre-signed URL for direct upload to CDN.

        Returns:
            Tuple of (upload_url, file_key)
            upload_url: The pre-signed URL to PUT the file to
            file_key: The unique identifier for the file (use this to construct public URL)
        """
        if not self.enabled or not self.s3_client:
            raise RuntimeError("CDN uploads not configured. Set CDN_ENABLED=true and configure credentials.")

        # Generate unique file key
        file_id = uuid.uuid4()
        prefix = f"vendors/{vendor_id}" if vendor_id else "uploads"
        file_key = f"{prefix}/{file_id}"

        # Determine content type and extension
        ext = self._get_extension(content_type)
        if ext:
            file_key = f"{file_key}.{ext}"

        try:
            upload_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key,
                    'ContentType': content_type,
                },
                ExpiresIn=300  # 5 minutes
            )

            logger.info("cdn.presigned_url_generated", file_key=file_key, vendor_id=str(vendor_id) if vendor_id else None)
            return upload_url, file_key

        except ClientError as e:
            logger.error("cdn.presign_failed", error=str(e))
            raise RuntimeError(f"Failed to generate upload URL: {e}")

    def get_public_url(self, file_key: str) -> str:
        """Get the public URL for a file."""
        if self.public_url_base:
            return f"{self.public_url_base}/{file_key}"

        # Construct from R2/S3 public endpoint if configured
        settings = get_settings()
        if self.enabled and settings.cdn_public_endpoint:
            return f"{settings.cdn_public_endpoint}/{self.bucket_name}/{file_key}"

        # Fallback: return the key (frontend should have base URL configured)
        return file_key

    def _get_extension(self, content_type: str) -> Optional[str]:
        """Map content type to file extension."""
        mapping = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
        }
        return mapping.get(content_type.lower())

    def validate_file_type(self, content_type: str) -> bool:
        """Validate that the file type is allowed."""
        allowed_types = {
            "image/jpeg", "image/jpg", "image/png", "image/webp"
        }
        return content_type.lower() in allowed_types


# Singleton instance
cdn_service = CDNService()
