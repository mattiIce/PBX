"""
CRM Integration and Screen Pop Support
Provides caller information lookup and CRM integration capabilities
"""
import json
import threading
from datetime import datetime
from typing import Dict, Optional, List, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from pbx.utils.logger import get_logger


class CallerInfo:
    """Represents caller information"""
    
    def __init__(self, phone_number: str):
        """
        Initialize caller info
        
        Args:
            phone_number: Phone number
        """
        self.phone_number = phone_number
        self.name = None
        self.company = None
        self.email = None
        self.account_id = None
        self.contact_id = None
        self.tags = []
        self.notes = None
        self.last_contact = None
        self.contact_count = 0
        self.custom_fields = {}
        self.source = None  # Source of the data (e.g., 'phone_book', 'crm', 'ad')
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'phone_number': self.phone_number,
            'name': self.name,
            'company': self.company,
            'email': self.email,
            'account_id': self.account_id,
            'contact_id': self.contact_id,
            'tags': self.tags,
            'notes': self.notes,
            'last_contact': self.last_contact.isoformat() if self.last_contact else None,
            'contact_count': self.contact_count,
            'custom_fields': self.custom_fields,
            'source': self.source
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'CallerInfo':
        """Create from dictionary"""
        phone_number = data.get('phone_number', '')
        caller_info = CallerInfo(phone_number)
        caller_info.name = data.get('name')
        caller_info.company = data.get('company')
        caller_info.email = data.get('email')
        caller_info.account_id = data.get('account_id')
        caller_info.contact_id = data.get('contact_id')
        caller_info.tags = data.get('tags', [])
        caller_info.notes = data.get('notes')
        caller_info.contact_count = data.get('contact_count', 0)
        caller_info.custom_fields = data.get('custom_fields', {})
        caller_info.source = data.get('source')
        
        if data.get('last_contact'):
            try:
                caller_info.last_contact = datetime.fromisoformat(data['last_contact'])
            except:
                pass
        
        return caller_info


class CRMLookupProvider:
    """Base class for CRM lookup providers"""
    
    def __init__(self, config: Dict):
        """
        Initialize CRM lookup provider
        
        Args:
            config: Provider configuration
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = config.get('enabled', False)
        self.name = config.get('name', 'Unknown')
    
    def lookup(self, phone_number: str) -> Optional[CallerInfo]:
        """
        Look up caller information
        
        Args:
            phone_number: Phone number to look up
            
        Returns:
            CallerInfo object if found, None otherwise
        """
        raise NotImplementedError("Subclasses must implement lookup()")


class PhoneBookLookupProvider(CRMLookupProvider):
    """Phone book lookup provider"""
    
    def __init__(self, config: Dict, phone_book=None):
        """
        Initialize phone book lookup provider
        
        Args:
            config: Provider configuration
            phone_book: Phone book instance
        """
        super().__init__(config)
        self.phone_book = phone_book
        self.name = 'PhoneBook'
    
    def lookup(self, phone_number: str) -> Optional[CallerInfo]:
        """Look up caller in phone book"""
        if not self.enabled or not self.phone_book:
            return None
        
        try:
            # Search phone book
            results = self.phone_book.search_contacts(phone_number)
            
            if results:
                contact = results[0]  # Take first match
                caller_info = CallerInfo(phone_number)
                caller_info.name = contact.get('name')
                caller_info.company = contact.get('company')
                caller_info.email = contact.get('email')
                caller_info.notes = contact.get('notes')
                caller_info.source = 'phone_book'
                return caller_info
        except Exception as e:
            self.logger.error(f"Phone book lookup error: {e}")
        
        return None


class ActiveDirectoryLookupProvider(CRMLookupProvider):
    """Active Directory lookup provider"""
    
    def __init__(self, config: Dict, ad_integration=None):
        """
        Initialize AD lookup provider
        
        Args:
            config: Provider configuration
            ad_integration: AD integration instance
        """
        super().__init__(config)
        self.ad_integration = ad_integration
        self.name = 'ActiveDirectory'
    
    def lookup(self, phone_number: str) -> Optional[CallerInfo]:
        """Look up caller in Active Directory"""
        if not self.enabled or not self.ad_integration:
            return None
        
        try:
            # Search AD by phone number
            users = self.ad_integration.search_users(f'(telephoneNumber={phone_number})')
            
            if users:
                user = users[0]  # Take first match
                caller_info = CallerInfo(phone_number)
                caller_info.name = user.get('displayName') or user.get('cn')
                caller_info.email = user.get('mail')
                caller_info.company = user.get('company')
                caller_info.source = 'active_directory'
                return caller_info
        except Exception as e:
            self.logger.error(f"Active Directory lookup error: {e}")
        
        return None


class ExternalCRMLookupProvider(CRMLookupProvider):
    """External CRM API lookup provider"""
    
    def __init__(self, config: Dict):
        """
        Initialize external CRM lookup provider
        
        Args:
            config: Provider configuration with 'url', 'api_key', 'timeout'
        """
        super().__init__(config)
        self.url = config.get('url')
        self.api_key = config.get('api_key')
        self.timeout = config.get('timeout', 5)
        self.name = config.get('name', 'ExternalCRM')
    
    def lookup(self, phone_number: str) -> Optional[CallerInfo]:
        """Look up caller via external CRM API"""
        if not self.enabled or not self.url:
            return None
        
        try:
            # Prepare request
            url = f"{self.url}?phone={phone_number}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'PBX-CRM/1.0'
            }
            
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            request = Request(url, headers=headers, method='GET')
            
            # Send request
            response = urlopen(request, timeout=self.timeout)
            data = json.loads(response.read().decode('utf-8'))
            
            # Parse response
            if data.get('found'):
                caller_info = CallerInfo(phone_number)
                caller_info.name = data.get('name')
                caller_info.company = data.get('company')
                caller_info.email = data.get('email')
                caller_info.account_id = data.get('account_id')
                caller_info.contact_id = data.get('contact_id')
                caller_info.tags = data.get('tags', [])
                caller_info.notes = data.get('notes')
                caller_info.custom_fields = data.get('custom_fields', {})
                caller_info.source = self.name.lower()
                
                if data.get('last_contact'):
                    try:
                        caller_info.last_contact = datetime.fromisoformat(data['last_contact'])
                    except:
                        pass
                
                if data.get('contact_count'):
                    caller_info.contact_count = int(data['contact_count'])
                
                return caller_info
        except (URLError, HTTPError) as e:
            self.logger.warning(f"External CRM lookup failed for {phone_number}: {e}")
        except Exception as e:
            self.logger.error(f"External CRM lookup error: {e}")
        
        return None


class CRMIntegration:
    """
    CRM Integration and Screen Pop System
    
    Provides:
    - Multi-source caller lookup (Phone Book, AD, External CRM)
    - Screen pop notifications via webhooks
    - Caller history tracking
    - Priority-based lookup (try multiple sources)
    """
    
    def __init__(self, config=None, pbx_core=None):
        """
        Initialize CRM integration
        
        Args:
            config: Configuration object
            pbx_core: PBX core instance
        """
        self.logger = get_logger()
        self.config = config or {}
        self.pbx_core = pbx_core
        
        # CRM configuration
        self.enabled = self._get_config('features.crm_integration.enabled', False)
        self.cache_enabled = self._get_config('features.crm_integration.cache_enabled', True)
        self.cache_timeout = self._get_config('features.crm_integration.cache_timeout', 3600)  # 1 hour
        
        # Lookup providers
        self.providers: List[CRMLookupProvider] = []
        
        # Lookup cache
        self.cache: Dict[str, tuple] = {}  # phone_number -> (CallerInfo, timestamp)
        self.cache_lock = threading.Lock()
        
        # Callbacks
        self.on_caller_identified: Optional[Callable] = None
        
        if self.enabled:
            self._initialize_providers()
            self.logger.info("CRM integration enabled")
        else:
            self.logger.info("CRM integration disabled")
    
    def _get_config(self, key: str, default=None):
        """Get configuration value"""
        if hasattr(self.config, 'get'):
            return self.config.get(key, default)
        return default
    
    def _initialize_providers(self):
        """Initialize CRM lookup providers"""
        providers_config = self._get_config('features.crm_integration.providers', [])
        
        for provider_config in providers_config:
            provider_type = provider_config.get('type')
            
            if provider_type == 'phone_book':
                phone_book = self.pbx_core.phone_book if self.pbx_core and hasattr(self.pbx_core, 'phone_book') else None
                provider = PhoneBookLookupProvider(provider_config, phone_book)
            elif provider_type == 'active_directory':
                ad_integration = self.pbx_core.ad_integration if self.pbx_core and hasattr(self.pbx_core, 'ad_integration') else None
                provider = ActiveDirectoryLookupProvider(provider_config, ad_integration)
            elif provider_type == 'external_crm':
                provider = ExternalCRMLookupProvider(provider_config)
            else:
                self.logger.warning(f"Unknown CRM provider type: {provider_type}")
                continue
            
            if provider.enabled:
                self.providers.append(provider)
                self.logger.info(f"Loaded CRM provider: {provider.name}")
    
    def lookup_caller(self, phone_number: str, use_cache: bool = True) -> Optional[CallerInfo]:
        """
        Look up caller information from all available sources
        
        Args:
            phone_number: Phone number to look up
            use_cache: Whether to use cached results
            
        Returns:
            CallerInfo object if found, None otherwise
        """
        if not self.enabled:
            return None
        
        # Normalize phone number (remove spaces, dashes, etc.)
        phone_number = self._normalize_phone_number(phone_number)
        
        # Check cache
        if use_cache and self.cache_enabled:
            caller_info = self._get_from_cache(phone_number)
            if caller_info:
                self.logger.debug(f"Caller lookup cache hit: {phone_number}")
                return caller_info
        
        # Try each provider in order
        for provider in self.providers:
            try:
                caller_info = provider.lookup(phone_number)
                if caller_info:
                    self.logger.info(f"Caller identified via {provider.name}: {phone_number} -> {caller_info.name}")
                    
                    # Cache result
                    if self.cache_enabled:
                        self._add_to_cache(phone_number, caller_info)
                    
                    # Notify callback
                    if self.on_caller_identified:
                        try:
                            self.on_caller_identified(phone_number, caller_info)
                        except Exception as e:
                            self.logger.error(f"Error in caller identified callback: {e}")
                    
                    return caller_info
            except Exception as e:
                self.logger.error(f"Error in {provider.name} lookup: {e}")
                continue
        
        self.logger.debug(f"Caller not found in any source: {phone_number}")
        return None
    
    def _normalize_phone_number(self, phone_number: str) -> str:
        """Normalize phone number for lookup"""
        # Remove common separators
        normalized = phone_number.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').replace('+', '')
        return normalized
    
    def _get_from_cache(self, phone_number: str) -> Optional[CallerInfo]:
        """Get caller info from cache"""
        with self.cache_lock:
            if phone_number in self.cache:
                caller_info, timestamp = self.cache[phone_number]
                age = (datetime.now() - timestamp).total_seconds()
                
                if age < self.cache_timeout:
                    return caller_info
                else:
                    # Cache expired
                    del self.cache[phone_number]
        
        return None
    
    def _add_to_cache(self, phone_number: str, caller_info: CallerInfo):
        """Add caller info to cache"""
        with self.cache_lock:
            self.cache[phone_number] = (caller_info, datetime.now())
    
    def clear_cache(self):
        """Clear lookup cache"""
        with self.cache_lock:
            self.cache.clear()
        self.logger.info("Caller lookup cache cleared")
    
    def trigger_screen_pop(self, phone_number: str, call_id: str, extension: str):
        """
        Trigger screen pop notification for incoming call
        
        Args:
            phone_number: Caller's phone number
            call_id: Call ID
            extension: Extension receiving the call
        """
        if not self.enabled:
            return
        
        # Look up caller info
        caller_info = self.lookup_caller(phone_number)
        
        # Prepare screen pop data
        screen_pop_data = {
            'call_id': call_id,
            'phone_number': phone_number,
            'extension': extension,
            'timestamp': datetime.now().isoformat(),
            'caller_info': caller_info.to_dict() if caller_info else None
        }
        
        # Trigger webhook event if webhook system is available
        if self.pbx_core and hasattr(self.pbx_core, 'webhook_system'):
            self.pbx_core.webhook_system.trigger_event('crm.screen_pop', screen_pop_data)
        
        self.logger.info(f"Screen pop triggered for call {call_id}: {phone_number} -> {extension}")
    
    def get_provider_status(self) -> List[Dict]:
        """Get status of all providers"""
        return [
            {
                'name': provider.name,
                'enabled': provider.enabled,
                'type': type(provider).__name__
            }
            for provider in self.providers
        ]
