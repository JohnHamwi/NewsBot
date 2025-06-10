"""
Media Validation Module

This module provides functionality to validate that images and videos
have been properly downloaded and are accessible.
"""

import os
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import hashlib
import mimetypes
import logging

logger = logging.getLogger(__name__)


class MediaValidator:
    """Validates media files and downloads."""
    
    def __init__(self, cache_dir: str = "data/cache/media"):
        """
        Initialize the media validator.
        
        Args:
            cache_dir: Directory to cache media files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported media types
        self.supported_image_types = {
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'
        }
        self.supported_video_types = {
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v'
        }
        
        # Maximum file sizes (in bytes)
        self.max_image_size = 50 * 1024 * 1024  # 50MB
        self.max_video_size = 500 * 1024 * 1024  # 500MB
        
        # Session for HTTP requests
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'NewsBot/2.0 Media Validator'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Generate hash for file content."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error generating hash for {file_path}: {e}")
            return ""
    
    def _get_cached_path(self, url: str) -> Path:
        """Get cached file path for URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}"
    
    async def _download_media(self, url: str, max_size: int) -> Optional[Path]:
        """
        Download media file from URL.
        
        Args:
            url: URL to download
            max_size: Maximum file size in bytes
            
        Returns:
            Path to downloaded file or None if failed
        """
        if not self.session:
            logger.error("Session not initialized. Use async context manager.")
            return None
        
        cached_path = self._get_cached_path(url)
        
        # Check if already cached
        if cached_path.exists():
            if cached_path.stat().st_size > 0:
                return cached_path
            else:
                # Remove empty file
                cached_path.unlink()
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download {url}: HTTP {response.status}")
                    return None
                
                # Check content length
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > max_size:
                    logger.warning(f"File too large: {url} ({content_length} bytes)")
                    return None
                
                # Download with size check
                total_size = 0
                async with aiofiles.open(cached_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        total_size += len(chunk)
                        if total_size > max_size:
                            logger.warning(f"File too large during download: {url}")
                            cached_path.unlink()
                            return None
                        await f.write(chunk)
                
                logger.info(f"Downloaded media: {url} -> {cached_path}")
                return cached_path
                
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            if cached_path.exists():
                cached_path.unlink()
            return None
    
    def _validate_image_file(self, file_path: Path) -> Dict[str, any]:
        """
        Validate an image file.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': False,
            'type': 'image',
            'format': None,
            'size': None,
            'dimensions': None,
            'file_size': 0,
            'error': None
        }
        
        try:
            if not file_path.exists():
                result['error'] = "File does not exist"
                return result
            
            result['file_size'] = file_path.stat().st_size
            
            if result['file_size'] == 0:
                result['error'] = "File is empty"
                return result
            
            if result['file_size'] > self.max_image_size:
                result['error'] = f"File too large ({result['file_size']} bytes)"
                return result
            
            # Basic validation - check file headers
            with open(file_path, 'rb') as f:
                header = f.read(12)
            
            # Check for common image file signatures
            image_signatures = [
                (b'\xff\xd8\xff', 'JPEG'),
                (b'\x89PNG\r\n\x1a\n', 'PNG'),
                (b'GIF87a', 'GIF'),
                (b'GIF89a', 'GIF'),
                (b'RIFF', 'WEBP'),  # WebP starts with RIFF
                (b'BM', 'BMP'),
            ]
            
            for sig, format_name in image_signatures:
                if header.startswith(sig):
                    result['format'] = format_name
                    result['valid'] = True
                    break
            
            if not result['valid']:
                result['error'] = "Not a valid image file"
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Image validation failed for {file_path}: {e}")
        
        return result
    
    def _validate_video_file(self, file_path: Path) -> Dict[str, any]:
        """
        Validate a video file.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': False,
            'type': 'video',
            'format': None,
            'file_size': 0,
            'error': None
        }
        
        try:
            if not file_path.exists():
                result['error'] = "File does not exist"
                return result
            
            result['file_size'] = file_path.stat().st_size
            
            if result['file_size'] == 0:
                result['error'] = "File is empty"
                return result
            
            if result['file_size'] > self.max_video_size:
                result['error'] = f"File too large ({result['file_size']} bytes)"
                return result
            
            # Basic validation - check if file has video extension and content
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type.startswith('video/'):
                result['format'] = mime_type
                result['valid'] = True
            else:
                # Try to read first few bytes to check for video headers
                with open(file_path, 'rb') as f:
                    header = f.read(12)
                    
                # Check for common video file signatures
                video_signatures = [
                    (b'\x00\x00\x00\x18ftypmp4', 'MP4'),
                    (b'\x00\x00\x00\x20ftypiso', 'MP4'),
                    (b'RIFF', 'AVI'),
                    (b'\x1a\x45\xdf\xa3', 'MKV'),
                ]
                
                for sig, format_name in video_signatures:
                    if header.startswith(sig):
                        result['valid'] = True
                        result['format'] = format_name
                        break
                
                if not result['valid']:
                    result['error'] = "Not a valid video file"
                    
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Video validation failed for {file_path}: {e}")
        
        return result
    
    async def validate_media_url(self, url: str) -> Dict[str, any]:
        """
        Validate media from URL by downloading and checking.
        
        Args:
            url: URL of media to validate
            
        Returns:
            Validation result dictionary
        """
        result = {
            'url': url,
            'valid': False,
            'type': 'unknown',
            'cached_path': None,
            'validation_details': None,
            'error': None
        }
        
        try:
            # Determine media type from URL
            url_lower = url.lower()
            is_image = any(url_lower.endswith(ext) for ext in self.supported_image_types)
            is_video = any(url_lower.endswith(ext) for ext in self.supported_video_types)
            
            if not is_image and not is_video:
                # Try to determine from content-type
                if self.session:
                    try:
                        async with self.session.head(url) as response:
                            content_type = response.headers.get('content-type', '').lower()
                            is_image = content_type.startswith('image/')
                            is_video = content_type.startswith('video/')
                    except:
                        pass
            
            if not is_image and not is_video:
                result['error'] = "Unsupported media type"
                return result
            
            # Download media
            max_size = self.max_image_size if is_image else self.max_video_size
            cached_path = await self._download_media(url, max_size)
            
            if not cached_path:
                result['error'] = "Failed to download media"
                return result
            
            result['cached_path'] = str(cached_path)
            
            # Validate downloaded file
            if is_image:
                result['type'] = 'image'
                validation = self._validate_image_file(cached_path)
            else:
                result['type'] = 'video'
                validation = self._validate_video_file(cached_path)
            
            result['validation_details'] = validation
            result['valid'] = validation['valid']
            
            if not result['valid']:
                result['error'] = validation.get('error', 'Validation failed')
                # Clean up invalid file
                if cached_path.exists():
                    cached_path.unlink()
                    result['cached_path'] = None
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Media validation failed for {url}: {e}")
        
        return result
    
    async def validate_media_urls(self, urls: List[str]) -> List[Dict[str, any]]:
        """
        Validate multiple media URLs concurrently.
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            List of validation results
        """
        if not urls:
            return []
        
        # Limit concurrent downloads
        semaphore = asyncio.Semaphore(5)
        
        async def validate_with_semaphore(url):
            async with semaphore:
                return await self.validate_media_url(url)
        
        tasks = [validate_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        validated_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                validated_results.append({
                    'url': urls[i],
                    'valid': False,
                    'error': str(result)
                })
            else:
                validated_results.append(result)
        
        return validated_results
    
    def cleanup_cache(self, max_age_days: int = 7):
        """
        Clean up old cached files.
        
        Args:
            max_age_days: Maximum age of files to keep
        """
        import time
        
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        cleaned_count = 0
        for file_path in self.cache_dir.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} old cached media files")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get statistics about cached media.
        
        Returns:
            Dictionary with cache statistics
        """
        total_files = 0
        total_size = 0
        image_count = 0
        video_count = 0
        
        for file_path in self.cache_dir.iterdir():
            if file_path.is_file():
                total_files += 1
                total_size += file_path.stat().st_size
                
                # Try to determine type
                try:
                    with Image.open(file_path):
                        image_count += 1
                except:
                    video_count += 1
        
        return {
            'total_files': total_files,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'image_count': image_count,
            'video_count': video_count,
            'cache_directory': str(self.cache_dir)
        }


# Convenience functions
async def validate_media_url(url: str) -> Dict[str, any]:
    """
    Convenience function to validate a single media URL.
    
    Args:
        url: URL to validate
        
    Returns:
        Validation result
    """
    async with MediaValidator() as validator:
        return await validator.validate_media_url(url)


async def validate_media_urls(urls: List[str]) -> List[Dict[str, any]]:
    """
    Convenience function to validate multiple media URLs.
    
    Args:
        urls: List of URLs to validate
        
    Returns:
        List of validation results
    """
    async with MediaValidator() as validator:
        return await validator.validate_media_urls(urls) 