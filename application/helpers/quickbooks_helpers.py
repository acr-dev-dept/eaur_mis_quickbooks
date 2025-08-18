import os
from cryptography.fernet import Fernet
from flask import current_app

# Load key from environment or secure location
fernet_key = os.environ.get("FERNET_KEY")
fernet = None

if fernet_key:
    try:
        fernet = Fernet(fernet_key)
    except Exception as e:
        print(f"Warning: Could not initialize Fernet encryption: {e}")
        fernet = None

class QuickBooksHelper:
    """
    A helper class for QuickBooks operations.
    """
    @classmethod
    def handle_quickbooks_response(cls, response: dict) -> tuple:
        """
        Handles the response from QuickBooks API.
        Args:
            response (dict): The response from QuickBooks API.
        Returns:
            tuple: A tuple containing the message and operation status.
        """
        from flask import current_app
        current_app.logger.info(f"Handling QuickBooks response: {response}")

        if "JournalEntry" in response:
            journal_entry = response["JournalEntry"]
            journal_id = journal_entry.get("Id")
            total_amount = journal_entry.get("TotalAmt")

            if journal_id:
                message = f"Journal entry posted successfully with ID: {journal_id} and total amount: {total_amount}"
                operation_status = "Success"
            else:
                message = "Journal entry response received but no ID found"
                operation_status = "Failure"

            current_app.logger.info(f"Journal entry response processed: {message}, status: {operation_status}")
            return message, operation_status

        elif "Fault" in response:
            fault = response["Fault"]
            message = fault["Error"][0].get("Message", "Unknown error occurred")
            detail = fault["Error"][0].get("Detail", "")
            current_app.logger.error(f"QuickBooks fault: {message}, detail: {detail}")
            return message, "Failure"

        # Log the full response for debugging unknown formats
        current_app.logger.error(f"Unknown QuickBooks response format: {response}")
        return "Unknown response format", "Failure"

    @classmethod
    def encrypt(cls, value: str) -> str:
        """Encrypts a string using Fernet."""
        try:
            if not value:
                current_app.logger.warning("Attempting to encrypt None or empty string")
                return None

            if not fernet:
                current_app.logger.warning("Fernet encryption not available - returning value as-is")
                return value

            encrypted = fernet.encrypt(value.encode()).decode()
            current_app.logger.info(f"Successfully encrypted value. Original length: {len(value)}, Encrypted length: {len(encrypted)}")
            return encrypted
        except Exception as e:
            current_app.logger.error(f"Error encrypting value: {str(e)}")
            raise

    @classmethod
    def decrypt(cls, encrypted_value: str) -> str:
        """Decrypts a Fernet-encrypted string."""
        try:
            if not encrypted_value:
                current_app.logger.warning("Attempting to decrypt None or empty string")
                return None

            if not fernet:
                current_app.logger.warning("Fernet encryption not available - returning value as-is")
                return encrypted_value

            decrypted = fernet.decrypt(encrypted_value.encode()).decode()
            current_app.logger.info(f"Successfully decrypted value. Encrypted length: {len(encrypted_value)}, Decrypted length: {len(decrypted)}")
            return decrypted
        except Exception as e:
            current_app.logger.error(f"Error decrypting value: {str(e)}")
            current_app.logger.error(f"Encrypted value that failed to decrypt: {encrypted_value}")
            raise