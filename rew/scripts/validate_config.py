#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Validator for Bot Setup
Перевіряє що всі необхідні параметри налаштовані правильно
"""

import json
import sys
from pathlib import Path

def validate_settings():
    """Validate settings.json configuration"""
    
    settings_path = Path(__file__).parent / "settings.json"
    
    print("=" * 60)
    print("🔍 Telegram Bot Configuration Validator")
    print("=" * 60)
    
    # Check if settings.json exists
    if not settings_path.exists():
        print(f"❌ ERROR: settings.json not found at {settings_path}")
        print(f"   Run: cp settings.json.example settings.json")
        return False
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in settings.json")
        print(f"   {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Cannot read settings.json")
        print(f"   {e}")
        return False
    
    # Required fields
    required = {
        'bot_token': 'Telegram Bot Token (from @BotFather)',
        'api_id': 'Telegram API ID (from my.telegram.org)',
        'api_hash': 'Telegram API Hash (from my.telegram.org)',
        'webapp_url': 'Web Application URL',
        'admin_ids': 'List of admin IDs',
    }
    
    errors = []
    warnings = []
    
    print("\n✅ Checking required fields:\n")
    
    for field, description in required.items():
        value = settings.get(field)
        
        if not value:
            errors.append(f"{field}: {description}")
            print(f"  ❌ {field}: MISSING")
            continue
        
        # Specific checks
        if field == 'bot_token':
            if not isinstance(value, str) or ':' not in value:
                errors.append(f"{field}: Invalid format (should be 'id:token')")
                print(f"  ❌ {field}: Invalid format")
            else:
                print(f"  ✅ {field}: Configured")
                
        elif field == 'api_id':
            if not isinstance(value, int) or value <= 0:
                errors.append(f"{field}: Must be a positive integer")
                print(f"  ❌ {field}: Invalid (must be number)")
            else:
                print(f"  ✅ {field}: {value}")
                
        elif field == 'api_hash':
            if not isinstance(value, str) or len(value) < 10:
                errors.append(f"{field}: Invalid format")
                print(f"  ❌ {field}: Invalid format")
            else:
                print(f"  ✅ {field}: Configured")
                
        elif field == 'webapp_url':
            if not isinstance(value, str) or not (value.startswith('http://') or value.startswith('https://')):
                errors.append(f"{field}: Must start with http:// or https://")
                print(f"  ❌ {field}: Invalid URL")
            else:
                print(f"  ✅ {field}: {value}")
                
        elif field == 'admin_ids':
            if not isinstance(value, list) or not value:
                errors.append(f"{field}: Must be a non-empty list")
                print(f"  ❌ {field}: Must be a list with at least one ID")
            else:
                print(f"  ✅ {field}: {value}")
    
    # Optional fields with defaults
    print("\n📋 Checking optional fields:\n")
    
    optional_fields = [
        ('workers', list, []),
        ('target_user', str, ''),
        ('maintenance_mode', bool, False),
        ('telegram_api_url', str, 'https://t.me'),
        ('about_link', str, 'https://t.me/IT_Portal'),
        ('nft_fragment_url', str, 'https://t.me/nft'),
        ('profit_channel_id', int, 0),
        ('logs_channel_id', int, 0),
    ]
    
    for field, field_type, default in optional_fields:
        value = settings.get(field)
        if value is None:
            warnings.append(f"{field}: Using default ({default})")
            print(f"  ⚠️  {field}: Not set (using default)")
        else:
            if not isinstance(value, field_type):
                warnings.append(f"{field}: Wrong type")
                print(f"  ⚠️  {field}: Wrong type")
            else:
                print(f"  ✅ {field}: Configured")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for error in errors:
            print(f"   • {error}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"   • {warning}")
    
    if not errors and not warnings:
        print("\n✅ All settings are correct!\n")
        print("You can now run:")
        print("   python scripts/main3.py")
        return True
    elif not errors:
        print("\n✅ Configuration is valid (with warnings)\n")
        print("You can now run:")
        print("   python scripts/main3.py")
        return True
    else:
        print(f"\n❌ Configuration has {len(errors)} error(s)\n")
        print("Please fix the errors above before running the bot.")
        return False

if __name__ == "__main__":
    success = validate_settings()
    sys.exit(0 if success else 1)
