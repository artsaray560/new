#!/usr/bin/env python3
"""
List all available gifts with their IDs and prices
"""

import asyncio
import json
from pathlib import Path
from pyrogram import Client

async def main():
    settings_path = Path(__file__).parent / "settings.json"
    with open(settings_path) as f:
        settings = json.load(f)
    
    phone = str(settings.get("gift_account_phone")).strip()
    api_id = settings.get("gift_account_api_id", settings.get("api_id"))
    api_hash = settings.get("gift_account_api_hash", settings.get("api_hash"))
    sessions_dir = Path(__file__).parent / "sessions"
    
    client = Client(
        f"gift_account_{phone}",
        api_id,
        api_hash,
        workdir=str(sessions_dir)
    )
    
    try:
        print("🔗 Connecting...")
        await client.connect()
        
        me = await client.get_me()
        print(f"✅ Connected as: @{me.username}\n")
        
        print("📦 Fetching available gifts...\n")
        gifts = await client.get_available_gifts()
        
        if not gifts:
            print("❌ No gifts available")
            return
        
        print(f"Found {len(gifts)} gifts:\n")
        print("=" * 80)
        print(f"{'ID':<20} {'Price':<10} {'Convert':<10} {'Title':<30} {'Sold Out'}")
        print("=" * 80)
        
        # Sort by price
        gifts_sorted = sorted(gifts, key=lambda g: g.price or 999)
        
        for gift in gifts_sorted:
            title = gift.title or f"Gift #{gift.id}"
            price = f"{gift.price}⭐" if gift.price else "?"
            convert = f"{gift.convert_price}⭐" if gift.convert_price else "?"
            sold_out = "YES" if gift.is_sold_out else "No"
            
            print(f"{gift.id:<20} {price:<10} {convert:<10} {title:<30} {sold_out}")
        
        print("\n" + "=" * 80)
        print("\nCheapest gifts (for auto-gift):")
        print("=" * 80)
        
        cheapest = [g for g in gifts_sorted if not g.is_sold_out][:5]
        for i, gift in enumerate(cheapest, 1):
            title = gift.title or f"Gift #{gift.id}"
            print(f"{i}. ID: {gift.id} | Price: {gift.price}⭐ | Convert: {gift.convert_price}⭐ | {title}")
        
        print("\n💡 Use these IDs in main3.py auto_gift_from_target() function")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if client.is_connected:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
