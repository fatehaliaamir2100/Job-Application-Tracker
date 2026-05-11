"""Gmail API client for fetching and processing emails."""
import os
import base64
from typing import List, Dict, Optional
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .config import settings

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailClient:
    """Client for interacting with Gmail API."""
    
    def __init__(self):
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth 2.0."""
        creds = None
        
        # Load existing token
        if os.path.exists(settings.gmail_token_file):
            creds = Credentials.from_authorized_user_file(
                settings.gmail_token_file, SCOPES
            )
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(settings.gmail_credentials_file):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {settings.gmail_credentials_file}\n"
                        "Please download from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.gmail_credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(settings.gmail_token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
    
    def search_job_emails(self, max_results: int = 50) -> List[Dict]:
        """
        Search for job-related emails.
        
        Args:
            max_results: Maximum number of emails to return
            
        Returns:
            List of email dictionaries with content
        """
        try:
            # Job-related search query
            query = (
                '(subject:(application OR interview OR position OR role OR '
                'opportunity OR recruiter OR hiring OR "thank you for applying" OR '
                '"we regret" OR "moving forward" OR "next steps")) OR '
                'from:(linkedin.com OR greenhouse.io OR lever.co OR workday.com OR '
                'indeed.com OR jobs@* OR recruiting@* OR talent@* OR hr@*)'
            )
            
            # Search messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return []
            
            # Fetch full message details
            emails = []
            for msg in messages:
                email_data = self._get_message_details(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def _get_message_details(self, message_id: str) -> Optional[Dict]:
        """Get detailed information about a specific message."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload'].get('headers', [])
            
            # Extract key headers
            subject = self._get_header(headers, 'Subject')
            from_email = self._get_header(headers, 'From')
            date_str = self._get_header(headers, 'Date')
            
            # Parse date
            try:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except:
                date = datetime.utcnow()
            
            # Get email body
            body = self._get_message_body(message['payload'])
            
            # Get snippet (preview)
            snippet = message.get('snippet', '')
            
            # Thread ID for grouping
            thread_id = message.get('threadId', '')
            
            return {
                'message_id': message_id,
                'thread_id': thread_id,
                'subject': subject,
                'from': from_email,
                'date': date,
                'snippet': snippet,
                'body': body
            }
            
        except HttpError as error:
            print(f'Error fetching message {message_id}: {error}')
            return None
    
    def _get_header(self, headers: List[Dict], name: str) -> str:
        """Extract a specific header value."""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return ''
    
    def _get_message_body(self, payload: Dict) -> str:
        """Extract message body from payload."""
        body = ''
        
        if 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
        else:
            # Simple message
            if 'data' in payload.get('body', {}):
                body = base64.urlsafe_b64decode(
                    payload['body']['data']
                ).decode('utf-8')
        
        return body
    
    def get_thread_messages(self, thread_id: str) -> List[Dict]:
        """Get all messages in a thread."""
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = []
            for msg in thread.get('messages', []):
                msg_data = self._get_message_details(msg['id'])
                if msg_data:
                    messages.append(msg_data)
            
            return messages
            
        except HttpError as error:
            print(f'Error fetching thread {thread_id}: {error}')
            return []
