"""
Media Service

This service handles all media downloading, processing, and file management
for the NewsBot. Extracted from fetch_view.py for better separation of concerns.
"""

import asyncio
import os
import tempfile
from typing import Optional, List, Tuple, Any
from tqdm import tqdm

from src.utils.base_logger import base_logger as logger
from src.utils import error_handler

# Configuration constants
DISCORD_MAX_FILESIZE_MB = int(os.getenv("DISCORD_MAX_FILESIZE_MB", "25"))
MAX_DISCORD_FILE_SIZE = DISCORD_MAX_FILESIZE_MB * 1024 * 1024


class MediaService:
    """Service for handling media downloads and processing."""

    def __init__(self, bot):
        """Initialize the media service with bot instance."""
        self.bot = bot
        self.logger = logger

    async def download_media_with_timeout(
        self,
        post: Any,
        media: Any,
        timeout: int = 45
    ) -> Tuple[Optional[List], Optional[str]]:
        """
        Download media from a Telegram post with timeout.

        Args:
            post: Telegram message object
            media: Media object from the post
            timeout: Download timeout in seconds

        Returns:
            Tuple of (media_files_list, temp_path) or (None, None) if failed
        """
        try:
            return await asyncio.wait_for(
                self._download_media_internal(post, media),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(f"[MEDIA] Media download timed out after {timeout} seconds")
            return None, None
        except Exception as e:
            self.logger.error(f"[MEDIA] Media download failed: {str(e)}")
            await error_handler.send_error_embed(
                "Media Download Error",
                e,
                context=f"Post ID: {getattr(post, 'id', 'unknown')}",
                bot=self.bot
            )
            return None, None

    async def _download_media_internal(
        self,
        post: Any,
        media: Any
    ) -> Tuple[Optional[List], Optional[str]]:
        """Internal media download logic."""
        media_files = []
        temp_path = None

        try:
            # Check if media is grouped (album)
            if hasattr(media, 'grouped_id') and media.grouped_id:
                self.logger.debug("[MEDIA] Processing grouped media (album)")
                media_files, temp_path = await self._download_grouped_media(post, media)
            else:
                self.logger.debug("[MEDIA] Processing single media file")
                media_files, temp_path = await self._download_single_media(post, media)

            return media_files, temp_path

        except Exception as e:
            self.logger.error(f"[MEDIA] Error in media download: {str(e)}")
            raise

    async def _download_grouped_media(
        self,
        post: Any,
        media: Any
    ) -> Tuple[List, Optional[str]]:
        """Download grouped media (album) from Telegram."""
        media_files = []
        temp_path = None

        try:
            # Get all messages in the group
            async def get_grouped_photos():
                messages = []
                async for message in self.bot.telegram_client.iter_messages(
                    post.peer_id,
                    limit=10,
                    offset_id=post.id + 5
                ):
                    if (hasattr(message, 'grouped_id') and
                            message.grouped_id == media.grouped_id):
                        messages.append(message)
                    if len(messages) >= 10:  # Safety limit
                        break
                return messages

            grouped_messages = await get_grouped_photos()
            self.logger.debug(f"[MEDIA] Found {len(grouped_messages)} grouped messages")

            if not grouped_messages:
                self.logger.warning("[MEDIA] No grouped messages found, falling back to single media")
                return await self._download_single_media(post, media)

            # Create temporary directory for grouped media
            temp_path = tempfile.mkdtemp(prefix="newsbot_grouped_")
            self.logger.debug(f"[MEDIA] Created temp directory: {temp_path}")

            # Download each media file in the group
            for i, msg in enumerate(grouped_messages):
                if not msg.media:
                    continue

                try:
                    # Progress callback for individual file
                    async def callback(current, total):
                        if total > 0:
                            percent = (current / total) * 100
                            self.logger.debug(
                                f"[MEDIA] Downloading file {i + 1}/{len(grouped_messages)}: {percent:.1f}%")

                    # Download the media file
                    file_path = await self.bot.telegram_client.download_media(
                        msg.media,
                        file=temp_path,
                        progress_callback=callback
                    )

                    if file_path and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        if file_size <= MAX_DISCORD_FILE_SIZE:
                            media_files.append(file_path)
                            self.logger.debug(
                                f"[MEDIA] Downloaded grouped file {i + 1}: "
                                f"{os.path.basename(file_path)} ({file_size} bytes)"
                            )
                        else:
                            self.logger.warning(
                                f"[MEDIA] Grouped file {i + 1} too large: "
                                f"{file_size} bytes > {MAX_DISCORD_FILE_SIZE}"
                            )
                            os.remove(file_path)

                except Exception as e:
                    self.logger.error(f"[MEDIA] Failed to download grouped file {i + 1}: {str(e)}")
                    continue

            self.logger.info(f"[MEDIA] Successfully downloaded {len(media_files)} grouped media files")
            return media_files, temp_path

        except Exception as e:
            self.logger.error(f"[MEDIA] Error downloading grouped media: {str(e)}")
            if temp_path and os.path.exists(temp_path):
                self._cleanup_temp_files([temp_path])
            raise

    async def _download_single_media(
        self,
        post: Any,
        media: Any
    ) -> Tuple[List, Optional[str]]:
        """Download single media file from Telegram."""
        media_files = []
        temp_path = None

        try:
            # Create temporary directory
            temp_path = tempfile.mkdtemp(prefix="newsbot_single_")
            self.logger.debug(f"[MEDIA] Created temp directory: {temp_path}")

            # Progress callback
            async def callback(current, total):
                if total > 0:
                    percent = (current / total) * 100
                    self.logger.debug(f"[MEDIA] Downloading single file: {percent:.1f}%")

            # Download the media file
            file_path = await self.bot.telegram_client.download_media(
                media,
                file=temp_path,
                progress_callback=callback
            )

            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                if file_size <= MAX_DISCORD_FILE_SIZE:
                    media_files.append(file_path)
                    self.logger.info(
                        f"[MEDIA] Downloaded single file: "
                        f"{os.path.basename(file_path)} ({file_size} bytes)"
                    )
                else:
                    self.logger.warning(f"[MEDIA] Single file too large: {file_size} bytes > {MAX_DISCORD_FILE_SIZE}")
                    os.remove(file_path)
                    media_files = []
            else:
                self.logger.warning("[MEDIA] No file downloaded or file doesn't exist")

            return media_files, temp_path

        except Exception as e:
            self.logger.error(f"[MEDIA] Error downloading single media: {str(e)}")
            if temp_path and os.path.exists(temp_path):
                self._cleanup_temp_files([temp_path])
            raise

    def _cleanup_temp_files(self, paths: List[str]) -> None:
        """Clean up temporary files and directories."""
        for path in paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    self.logger.debug(f"[MEDIA] Cleaned up temp file: {path}")
                elif os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                    self.logger.debug(f"[MEDIA] Cleaned up temp directory: {path}")
            except Exception as e:
                self.logger.warning(f"[MEDIA] Failed to cleanup {path}: {str(e)}")

    def cleanup_media_files(self, media_files: List[str], temp_path: Optional[str]) -> None:
        """Public method to cleanup media files after use."""
        cleanup_paths = []

        # Add individual files
        if media_files:
            cleanup_paths.extend(media_files)

        # Add temp directory
        if temp_path:
            cleanup_paths.append(temp_path)

        if cleanup_paths:
            self._cleanup_temp_files(cleanup_paths)
            self.logger.debug(f"[MEDIA] Cleaned up {len(cleanup_paths)} media items")

    def validate_media_files(self, media_files: List[str]) -> List[str]:
        """Validate and filter media files that exist and are within size limits."""
        valid_files = []

        for file_path in media_files:
            if not os.path.exists(file_path):
                self.logger.warning(f"[MEDIA] File doesn't exist: {file_path}")
                continue

            file_size = os.path.getsize(file_path)
            if file_size > MAX_DISCORD_FILE_SIZE:
                self.logger.warning(f"[MEDIA] File too large: {file_path} ({file_size} bytes)")
                continue

            valid_files.append(file_path)

        self.logger.debug(f"[MEDIA] Validated {len(valid_files)}/{len(media_files)} media files")
        return valid_files
