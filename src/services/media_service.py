# =============================================================================
# NewsBot Media Service Module
# =============================================================================
# Media downloading, processing, and file management for the NewsBot
# Extracted from fetch_view.py for better separation of concerns
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import os
import tempfile
import time
from typing import Any, List, Optional, Tuple

# =============================================================================
# Third-Party Library Imports
# =============================================================================
from tqdm import tqdm

# =============================================================================
# Local Application Imports
# =============================================================================
from src.utils import error_handler
from src.utils.base_logger import base_logger as logger
from src.utils.media_validator import MediaValidator

# =============================================================================
# Configuration Constants
# =============================================================================
DISCORD_MAX_FILESIZE_MB = 100  # Discord file size limit in MB
MAX_DISCORD_FILE_SIZE = DISCORD_MAX_FILESIZE_MB * 1024 * 1024

# =============================================================================
# Media Service Class
# =============================================================================

class MediaService:
    """Service for handling media downloads and processing."""

    def __init__(self, bot):
        """Initialize the media service with bot instance."""
        self.bot = bot
        self.logger = logger
        self.media_validator = MediaValidator()

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _format_time(self, seconds: float) -> str:
        """Format time in human readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    async def download_media_with_timeout(
        self, post: Any, media: Any, timeout: int = 180
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
        start_time = time.time()
        self.logger.info(f"[MEDIA] Starting media download (timeout: {timeout}s)")

        try:
            return await asyncio.wait_for(
                self._download_media_internal(post, media), timeout=timeout
            )
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            self.logger.error(
                f"[MEDIA] ⏰ Media download timed out after {elapsed:.1f}s (limit: {timeout}s)"
            )
            return None, None
        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(
                f"[MEDIA] ❌ Media download failed after {elapsed:.1f}s: {str(e)}"
            )
            await error_handler.send_error_embed(
                "Media Download Error",
                e,
                context=f"Post ID: {getattr(post, 'id', 'unknown')}",
                bot=self.bot,
            )
            return None, None

    async def _download_media_internal(
        self, post: Any, media: Any
    ) -> Tuple[Optional[List], Optional[str]]:
        """Internal media download logic."""
        media_files = []
        temp_path = None

        try:
            # Check if media is grouped (album)
            if hasattr(media, "grouped_id") and media.grouped_id:
                self.logger.info("[MEDIA] 📁 Processing grouped media (album)")
                media_files, temp_path = await self._download_grouped_media(post, media)
            else:
                self.logger.info("[MEDIA] 📄 Processing single media file")
                media_files, temp_path = await self._download_single_media(post, media)

            return media_files, temp_path

        except Exception as e:
            self.logger.error(f"[MEDIA] Error in media download: {str(e)}")
            raise

    async def _download_grouped_media(
        self, post: Any, media: Any
    ) -> Tuple[List, Optional[str]]:
        """Download grouped media (album) from Telegram."""
        media_files = []
        temp_path = None

        try:
            # Get all messages in the group
            async def get_grouped_photos():
                """Get all messages in a grouped media album from Telegram."""
                messages = []
                async for message in self.bot.telegram_client.iter_messages(
                    post.peer_id, limit=10, offset_id=post.id + 5
                ):
                    if (
                        hasattr(message, "grouped_id")
                        and message.grouped_id == media.grouped_id
                    ):
                        messages.append(message)
                    if len(messages) >= 10:  # Safety limit
                        break
                return messages

            grouped_messages = await get_grouped_photos()
            self.logger.info(f"[MEDIA] 📊 Found {len(grouped_messages)} files in album")

            if not grouped_messages:
                self.logger.warning(
                    "[MEDIA] No grouped messages found, falling back to single media"
                )
                return await self._download_single_media(post, media)

            # Create temporary directory for grouped media
            temp_path = tempfile.mkdtemp(prefix="newsbot_grouped_")
            self.logger.debug(f"[MEDIA] Created temp directory: {temp_path}")

            # Download each media file in the group
            for i, msg in enumerate(grouped_messages):
                if not msg.media:
                    continue

                try:
                    file_start_time = time.time()
                    last_progress_time = time.time()

                    # Enhanced progress callback for album files
                    async def callback(current, total):
                        nonlocal last_progress_time
                        current_time = time.time()

                        # Only log progress every 2 seconds to avoid spam
                        if current_time - last_progress_time >= 2.0 or current == total:
                            if total > 0:
                                percent = (current / total) * 100
                                elapsed = current_time - file_start_time

                                if current > 0 and elapsed > 0:
                                    speed = current / elapsed  # bytes per second
                                    remaining_bytes = total - current
                                    eta = remaining_bytes / speed if speed > 0 else 0

                                    # Create progress bar
                                    bar_length = 20
                                    filled_length = int(bar_length * current // total)
                                    bar = "█" * filled_length + "░" * (
                                        bar_length - filled_length
                                    )

                                    progress_msg = (
                                        f"[MEDIA] 📥 File {i + 1}/{len(grouped_messages)} [{bar}] {percent:.1f}% "
                                        f"({self._format_file_size(current)}/{self._format_file_size(total)}) "
                                        f"- {self._format_file_size(speed)}/s - ETA: {self._format_time(eta)}"
                                    )

                                    if current == total:
                                        # Final message - use normal logging
                                        self.logger.info(progress_msg)
                                    else:
                                        # Progress update - print with carriage return to overwrite
                                        print(f"\r{progress_msg}", end="", flush=True)
                                else:
                                    progress_msg = (
                                        f"[MEDIA] 📥 File {i + 1}/{len(grouped_messages)} Downloading: {percent:.1f}% "
                                        f"({self._format_file_size(current)}/{self._format_file_size(total)})"
                                    )
                                    if current == total:
                                        self.logger.info(progress_msg)
                                    else:
                                        print(f"\r{progress_msg}", end="", flush=True)
                            last_progress_time = current_time

                    # Download the media file
                    self.logger.info(
                        f"[MEDIA] 🚀 Starting download of file {i + 1}/{len(grouped_messages)}"
                    )
                    file_path = await self.bot.telegram_client.download_media(
                        msg.media, file=temp_path, progress_callback=callback
                    )

                    # Ensure we have a newline after progress bar
                    print()

                    if file_path and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        download_time = time.time() - file_start_time

                        if file_size <= MAX_DISCORD_FILE_SIZE:
                            media_files.append(file_path)
                            self.logger.info(
                                f"[MEDIA] ✅ Downloaded file {i + 1}/{len(grouped_messages)}: "
                                f"{os.path.basename(file_path)} ({self._format_file_size(file_size)}) "
                                f"in {self._format_time(download_time)}"
                            )
                        else:
                            self.logger.warning(
                                f"[MEDIA] ⚠️ File {i + 1} too large: "
                                f"{self._format_file_size(file_size)} > {self._format_file_size(MAX_DISCORD_FILE_SIZE)}"
                            )
                            os.remove(file_path)

                except Exception as e:
                    # Ensure we have a newline after progress bar in case of error
                    print()
                    self.logger.error(
                        f"[MEDIA] ❌ Failed to download file {i + 1}/{len(grouped_messages)}: {str(e)}"
                    )
                    continue

            self.logger.info(
                f"[MEDIA] 🎉 Successfully downloaded {len(media_files)}/{len(grouped_messages)} album files"
            )
            return media_files, temp_path

        except Exception as e:
            self.logger.error(f"[MEDIA] Error downloading grouped media: {str(e)}")
            if temp_path and os.path.exists(temp_path):
                self._cleanup_temp_files([temp_path])
            raise

    async def _download_single_media(
        self, post: Any, media: Any
    ) -> Tuple[List, Optional[str]]:
        """Download single media file from Telegram."""
        media_files = []
        temp_path = None

        try:
            # Create temporary directory
            temp_path = tempfile.mkdtemp(prefix="newsbot_single_")
            self.logger.debug(f"[MEDIA] Created temp directory: {temp_path}")

            start_time = time.time()
            last_progress_time = time.time()
            progress_logged = False

            # Enhanced progress callback with progress bar
            async def callback(current, total):
                nonlocal last_progress_time, progress_logged
                current_time = time.time()

                # Only log progress every 2 seconds to avoid spam
                if current_time - last_progress_time >= 2.0 or current == total:
                    if total > 0:
                        percent = (current / total) * 100
                        elapsed = current_time - start_time

                        if current > 0 and elapsed > 0:
                            speed = current / elapsed  # bytes per second
                            remaining_bytes = total - current
                            eta = remaining_bytes / speed if speed > 0 else 0

                            # Create progress bar
                            bar_length = 20
                            filled_length = int(bar_length * current // total)
                            bar = "█" * filled_length + "░" * (
                                bar_length - filled_length
                            )

                            progress_msg = (
                                f"[MEDIA] 📥 [{bar}] {percent:.1f}% "
                                f"({self._format_file_size(current)}/{self._format_file_size(total)}) "
                                f"- {self._format_file_size(speed)}/s - ETA: {self._format_time(eta)}"
                            )

                            if current == total:
                                # Final message - use normal logging
                                self.logger.info(progress_msg)
                                progress_logged = True
                            else:
                                # Progress update - print with carriage return to overwrite
                                print(f"\r{progress_msg}", end="", flush=True)
                        else:
                            progress_msg = (
                                f"[MEDIA] 📥 Downloading: {percent:.1f}% "
                                f"({self._format_file_size(current)}/{self._format_file_size(total)})"
                            )
                            if current == total:
                                self.logger.info(progress_msg)
                                progress_logged = True
                            else:
                                print(f"\r{progress_msg}", end="", flush=True)
                    last_progress_time = current_time

            # Download the media file
            self.logger.info("[MEDIA] 🚀 Starting single file download")
            file_path = await self.bot.telegram_client.download_media(
                media, file=temp_path, progress_callback=callback
            )

            # Ensure we have a newline after progress bar
            if not progress_logged:
                print()  # Add newline to clear progress bar

            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                download_time = time.time() - start_time

                if file_size <= MAX_DISCORD_FILE_SIZE:
                    media_files.append(file_path)
                    self.logger.info(
                        f"[MEDIA] ✅ Downloaded: {os.path.basename(file_path)} "
                        f"({self._format_file_size(file_size)}) in {self._format_time(download_time)}"
                    )
                else:
                    self.logger.warning(
                        f"[MEDIA] ⚠️ File too large: {self._format_file_size(file_size)} > "
                        f"{self._format_file_size(MAX_DISCORD_FILE_SIZE)}"
                    )
                    os.remove(file_path)
                    media_files = []
            else:
                self.logger.warning(
                    "[MEDIA] ❌ No file downloaded or file doesn't exist"
                )

            return media_files, temp_path

        except Exception as e:
            # Ensure we have a newline after progress bar in case of error
            print()
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

    def cleanup_media_files(
        self, media_files: List[str], temp_path: Optional[str]
    ) -> None:
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
        """Validate and filter media files that exist and are properly formatted."""
        valid_files = []

        for file_path in media_files:
            if not os.path.exists(file_path):
                self.logger.warning(f"[MEDIA] File doesn't exist: {file_path}")
                continue

            file_size = os.path.getsize(file_path)
            if file_size > MAX_DISCORD_FILE_SIZE:
                self.logger.warning(
                    f"[MEDIA] File too large: {file_path} ({file_size} bytes)"
                )
                continue

            # Enhanced validation using MediaValidator
            try:
                from pathlib import Path

                path_obj = Path(file_path)

                # Determine file type and validate accordingly
                file_ext = path_obj.suffix.lower()

                if file_ext in {
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".gif",
                    ".webp",
                    ".bmp",
                    ".tiff",
                }:
                    # Validate image
                    validation_result = self.media_validator._validate_image_file(
                        path_obj
                    )
                elif file_ext in {
                    ".mp4",
                    ".avi",
                    ".mov",
                    ".wmv",
                    ".flv",
                    ".webm",
                    ".mkv",
                    ".m4v",
                }:
                    # Validate video
                    validation_result = self.media_validator._validate_video_file(
                        path_obj
                    )
                else:
                    # Unknown file type, skip validation but allow
                    self.logger.debug(
                        f"[MEDIA] Unknown file type, allowing: {file_path}"
                    )
                    valid_files.append(file_path)
                    continue

                if validation_result["valid"]:
                    valid_files.append(file_path)
                    self.logger.debug(
                        f"[MEDIA] Validated {validation_result['type']}: {file_path}"
                    )
                else:
                    self.logger.warning(
                        f"[MEDIA] Invalid {validation_result['type']}: {file_path} - {validation_result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                self.logger.error(f"[MEDIA] Error validating {file_path}: {str(e)}")
                # If validation fails, still include the file (fallback)
                valid_files.append(file_path)

        self.logger.info(
            f"[MEDIA] Validated {len(valid_files)}/{len(media_files)} media files"
        )
        return valid_files
