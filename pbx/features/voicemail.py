"""
Voicemail system
"""
import os
from datetime import datetime
from pbx.utils.logger import get_logger


class VoicemailBox:
    """Represents a voicemail box for an extension"""
    
    def __init__(self, extension_number, storage_path="voicemail"):
        """
        Initialize voicemail box
        
        Args:
            extension_number: Extension number
            storage_path: Path to store voicemail files
        """
        self.extension_number = extension_number
        self.storage_path = os.path.join(storage_path, extension_number)
        self.messages = []
        self.logger = get_logger()
        
        # Create storage directory
        os.makedirs(self.storage_path, exist_ok=True)
    
    def save_message(self, caller_id, audio_data):
        """
        Save voicemail message
        
        Args:
            caller_id: ID of caller
            audio_data: Audio data bytes
            
        Returns:
            Message ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        message_id = f"{caller_id}_{timestamp}"
        
        file_path = os.path.join(self.storage_path, f"{message_id}.wav")
        
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        message = {
            'id': message_id,
            'caller_id': caller_id,
            'timestamp': datetime.now(),
            'file_path': file_path,
            'listened': False
        }
        
        self.messages.append(message)
        self.logger.info(f"Saved voicemail for extension {self.extension_number}")
        
        return message_id
    
    def get_messages(self, unread_only=False):
        """
        Get voicemail messages
        
        Args:
            unread_only: Only return unread messages
            
        Returns:
            List of message dictionaries
        """
        if unread_only:
            return [msg for msg in self.messages if not msg['listened']]
        return self.messages
    
    def mark_listened(self, message_id):
        """
        Mark message as listened
        
        Args:
            message_id: Message identifier
        """
        for msg in self.messages:
            if msg['id'] == message_id:
                msg['listened'] = True
                break
    
    def delete_message(self, message_id):
        """
        Delete message
        
        Args:
            message_id: Message identifier
            
        Returns:
            True if deleted
        """
        for i, msg in enumerate(self.messages):
            if msg['id'] == message_id:
                # Delete file
                if os.path.exists(msg['file_path']):
                    os.remove(msg['file_path'])
                
                # Remove from list
                self.messages.pop(i)
                self.logger.info(f"Deleted voicemail {message_id}")
                return True
        return False


class VoicemailSystem:
    """Manages voicemail for all extensions"""
    
    def __init__(self, storage_path="voicemail"):
        """
        Initialize voicemail system
        
        Args:
            storage_path: Path to store voicemail files
        """
        self.storage_path = storage_path
        self.mailboxes = {}
        self.logger = get_logger()
        
        os.makedirs(storage_path, exist_ok=True)
    
    def get_mailbox(self, extension_number):
        """
        Get or create mailbox for extension
        
        Args:
            extension_number: Extension number
            
        Returns:
            VoicemailBox object
        """
        if extension_number not in self.mailboxes:
            self.mailboxes[extension_number] = VoicemailBox(
                extension_number,
                self.storage_path
            )
        return self.mailboxes[extension_number]
    
    def save_message(self, extension_number, caller_id, audio_data):
        """
        Save voicemail message
        
        Args:
            extension_number: Extension to save message for
            caller_id: Caller ID
            audio_data: Audio data
            
        Returns:
            Message ID
        """
        mailbox = self.get_mailbox(extension_number)
        return mailbox.save_message(caller_id, audio_data)
    
    def get_message_count(self, extension_number, unread_only=True):
        """
        Get message count for extension
        
        Args:
            extension_number: Extension number
            unread_only: Only count unread messages
            
        Returns:
            Message count
        """
        mailbox = self.get_mailbox(extension_number)
        return len(mailbox.get_messages(unread_only))
