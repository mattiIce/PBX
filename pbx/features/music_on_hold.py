"""
Music on Hold (MOH) System
Plays audio while calls are on hold
"""

import os
import random

from pbx.utils.logger import get_logger


class MusicOnHold:
    """Manages music on hold"""

    def __init__(self, moh_directory="moh", default_class="default"):
        """
        Initialize MOH system

        Args:
            moh_directory: Directory containing MOH files
            default_class: Default MOH class name
        """
        self.moh_directory = moh_directory
        self.default_class = default_class
        self.classes = {}  # class_name -> list of audio files
        self.logger = get_logger()
        self.active_sessions = {}  # call_id -> current playing file

        os.makedirs(moh_directory, exist_ok=True)
        self._load_classes()

    def _load_classes(self):
        """Load MOH classes and files"""
        # Create default class if it doesn't exist
        default_path = os.path.join(self.moh_directory, self.default_class)
        os.makedirs(default_path, exist_ok=True)

        # Scan for MOH classes (subdirectories)
        if os.path.exists(self.moh_directory):
            for item in os.listdir(self.moh_directory):
                class_path = os.path.join(self.moh_directory, item)
                if os.path.isdir(class_path):
                    audio_files = self._scan_audio_files(class_path)
                    if audio_files:
                        self.classes[item] = audio_files
                        self.logger.info(
                            f"Loaded MOH class '{item}' with {len(audio_files)} files"
                        )

    def _scan_audio_files(self, directory):
        """
        Scan directory for audio files

        Args:
            directory: Directory to scan

        Returns:
            list of audio file paths
        """
        audio_extensions = [".wav", ".mp3", ".ogg", ".flac", ".aac"]
        audio_files = []

        for filename in os.listdir(directory):
            if any(filename.lower().endswith(ext) for ext in audio_extensions):
                audio_files.append(os.path.join(directory, filename))

        return sorted(audio_files)

    def start_moh(self, call_id, moh_class=None):
        """
        Start music on hold for call

        Args:
            call_id: Call identifier
            moh_class: MOH class name (or None for default)

        Returns:
            Path to audio file or None
        """
        if moh_class is None:
            moh_class = self.default_class

        audio_files = self.classes.get(moh_class, [])

        if not audio_files:
            self.logger.warning(f"No MOH files found for class '{moh_class}'")
            return None

        # Select random file
        audio_file = random.choice(audio_files)
        self.active_sessions[call_id] = {
            "class": moh_class,
            "file": audio_file,
            "files": audio_files,
            "index": audio_files.index(audio_file),
        }

        self.logger.debug(f"Started MOH for call {call_id}: {audio_file}")
        return audio_file

    def stop_moh(self, call_id):
        """
        Stop music on hold

        Args:
            call_id: Call identifier
        """
        if call_id in self.active_sessions:
            del self.active_sessions[call_id]
            self.logger.debug(f"Stopped MOH for call {call_id}")

    def get_next_file(self, call_id):
        """
        Get next file in sequence for call

        Args:
            call_id: Call identifier

        Returns:
            Path to next audio file
        """
        session = self.active_sessions.get(call_id)

        if not session:
            return None

        files = session["files"]
        index = (session["index"] + 1) % len(files)

        session["index"] = index
        session["file"] = files[index]

        return files[index]

    def add_moh_class(self, class_name, files):
        """
        Add MOH class

        Args:
            class_name: Name of MOH class
            files: list of audio file paths
        """
        self.classes[class_name] = files
        self.logger.info(
            f"Added MOH class '{class_name}' with {len(files)} files"
        )

    def get_classes(self):
        """Get list of available MOH classes"""
        return list(self.classes.keys())

    def get_class_files(self, class_name):
        """
        Get files in MOH class

        Args:
            class_name: MOH class name

        Returns:
            list of file paths
        """
        return self.classes.get(class_name, [])
