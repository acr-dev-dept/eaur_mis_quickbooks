"""
Bank Synchronization Configuration for EAUR MIS-QuickBooks Integration

This configuration handles multiple environments and currency scenarios:
1. SANDBOX: USD base currency (for testing)
2. LIVE: RWF base currency (production)
3. MULTI_CURRENCY: Full multi-currency support (future)
"""

class BankSyncConfig:
    """Configuration for bank synchronization service"""

    # Environment settings - Change this for different environments
    ENVIRONMENT = "SANDBOX"  # Options: "SANDBOX", "LIVE", "MULTI_CURRENCY"

    # For sandbox testing, you can also enable multi-currency in your QB sandbox:
    # 1. Log into QuickBooks Online Sandbox
    # 2. Go to Settings → Account and Settings → Advanced
    # 3. Enable Multi-currency and add RWF as a currency
    # 4. This will allow proper RWF bank accounts in sandbox

    # Currency handling strategies
    CURRENCY_STRATEGIES = {
        'OMIT': 'omit_currency_ref',      # Don't include CurrencyRef (use QB base currency)
        'FORCE_BASE': 'force_base_currency',  # Force QB base currency in CurrencyRef
        'MATCH_BANK': 'match_bank_currency',  # Use bank's actual currency
        'AUTO_DETECT': 'auto_detect'      # Automatically detect best strategy
    }

    # Default strategy per environment
    DEFAULT_STRATEGY = "AUTO_DETECT"

    # Logging settings
    LOG_CURRENCY_DECISIONS = True
    LOG_ACCOUNT_CREATION = True
    
    @classmethod
    def get_config_for_environment(cls, environment: str = None):
        """
        Get configuration based on environment
        
        Args:
            environment (str): 'LIVE' or 'SANDBOX'
            
        Returns:
            dict: Configuration dictionary
        """
        env = environment or cls.ENVIRONMENT
        
        if env == "LIVE":
            return {
                'single_currency_mode': True,
                'base_currency': 'RWF',
                'include_currency_ref': False,  # Skip CurrencyRef for single-currency
                'description_prefix': 'EAUR MIS Bank ID',
                'account_type': 'Bank',
                'account_subtype': 'Checking'
            }
        elif env == "SANDBOX":
            return {
                'single_currency_mode': False,
                'base_currency': 'USD',
                'include_currency_ref': True,  # Include CurrencyRef for testing
                'description_prefix': 'TEST MIS Bank ID',
                'account_type': 'Bank',
                'account_subtype': 'Checking'
            }
        else:
            # Default to live settings
            return cls.get_config_for_environment("LIVE")
    
    @classmethod
    def is_live_environment(cls):
        """Check if running in live environment"""
        return cls.ENVIRONMENT == "LIVE"
    
    @classmethod
    def is_sandbox_environment(cls):
        """Check if running in sandbox environment"""
        return cls.ENVIRONMENT == "SANDBOX"


# Environment-specific configurations
SANDBOX_CONFIG = {
    'environment': 'SANDBOX',
    'qb_base_currency': 'USD',           # QuickBooks sandbox uses USD
    'mis_primary_currency': 'RWF',       # MIS banks are in RWF
    'currency_strategy': 'AUTO_DETECT',   # Let system decide best approach
    'enable_multi_currency_detection': True,  # Check if QB has multi-currency enabled
    'fallback_to_base_currency': True,   # If multi-currency disabled, use QB base currency
    'log_prefix': '[SANDBOX]',
    'description_template': 'TEST MIS Bank ID: {bank_id} - {bank_name} {bank_branch}',
    'account_name_template': '{bank_name} - {bank_branch}'
}

LIVE_CONFIG = {
    'environment': 'LIVE',
    'qb_base_currency': 'RWF',           # QuickBooks live uses RWF
    'mis_primary_currency': 'RWF',       # MIS banks are in RWF
    'currency_strategy': 'OMIT',         # Perfect match - omit CurrencyRef
    'enable_multi_currency_detection': False,  # Not needed when currencies match
    'fallback_to_base_currency': False,  # Not needed when currencies match
    'log_prefix': '[LIVE]',
    'description_template': 'EAUR MIS Bank ID: {bank_id} - {bank_name} {bank_branch}',
    'account_name_template': '{bank_name} - {bank_branch}'
}

MULTI_CURRENCY_CONFIG = {
    'environment': 'MULTI_CURRENCY',
    'qb_base_currency': 'RWF',           # Primary currency
    'mis_primary_currency': 'RWF',       # Primary currency
    'currency_strategy': 'MATCH_BANK',   # Use each bank's specific currency
    'enable_multi_currency_detection': True,  # Always check multi-currency status
    'fallback_to_base_currency': False,  # Use specific currencies
    'log_prefix': '[MULTI]',
    'description_template': 'EAUR MIS Bank ID: {bank_id} - {bank_name} {bank_branch} ({currency})',
    'account_name_template': '{bank_name} - {bank_branch} ({currency})'
}

# Default configuration based on environment setting
def get_default_config():
    """Get default configuration based on ENVIRONMENT setting"""
    config_map = {
        'SANDBOX': SANDBOX_CONFIG,
        'LIVE': LIVE_CONFIG,
        'MULTI_CURRENCY': MULTI_CURRENCY_CONFIG
    }
    return config_map.get(BankSyncConfig.ENVIRONMENT, SANDBOX_CONFIG)

DEFAULT_CONFIG = get_default_config()
