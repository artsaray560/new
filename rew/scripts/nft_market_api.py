"""NFT Market Price API Functions - Using Getgems REST API with Bearer Token"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Getgems API configuration
GETGEMS_API_KEY = "1767161530042-mainnet-10710520-r-dlk9q1DeUcpxCD7eXGBIpYXtq47FV0OfGaehpVPrt5QVEZr1"
GETGEMS_API_BASE = "https://api.getgems.io/public-api/v1"

# Telegram gifts collection address (verify on https://getgems.io/)
TELEGRAM_GIFTS_COLLECTION = "EQCA14o1-VWhS2efqoh_9M1b_A9DtKTuoqfmkn83AbJzwnPi"
DEFAULT_COLLECTION_ADDRESS = TELEGRAM_GIFTS_COLLECTION


async def get_nft_price_from_getgems(collection_address: Optional[str] = None) -> Optional[Dict]:
    """
    Get NFT collection floor price from Getgems REST API
    Returns: {'ton': price, 'usd': price_in_usd, 'market': 'GetGems', 'items_count': count}
    """
    try:
        if not collection_address:
            collection_address = TELEGRAM_GIFTS_COLLECTION
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {GETGEMS_API_KEY}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Get NFTs on sale in collection to find floor price
            url = f"{GETGEMS_API_BASE}/nfts/on-sale/{collection_address}"
            
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get('success') and data.get('response'):
                        items = data['response'].get('items', [])
                        
                        if items:
                            # Get floor price from first item (cheapest)
                            floor_item = items[0]
                            sale_data = floor_item.get('sale', {})
                            
                            # Extract price from sale data
                            # API returns 'fullPrice' for FixPriceSale, 'minBid' for auction
                            if sale_data.get('type') in ('Auction', 'AuctionSale'):
                                price_str = sale_data.get('minBid', '0')
                            elif sale_data.get('type') in ('FixedPrice', 'FixPriceSale'):
                                price_str = sale_data.get('fullPrice') or sale_data.get('price', '0')
                            else:
                                # Fallback: try fullPrice first, then price, then minBid
                                price_str = sale_data.get('fullPrice') or sale_data.get('price') or sale_data.get('minBid', '0')
                            
                            # Convert from nanotons to TON (1 TON = 1e9 nanotons)
                            ton_price = float(price_str) / 1e9 if price_str else 0
                            
                            if ton_price > 0:
                                logger.info(f"GetGems floor price: {ton_price} TON ({len(items)} items on sale)")
                                return {
                                    'ton': round(ton_price, 4),
                                    'usd': round(ton_price * 5.0, 2),
                                    'market': 'GetGems',
                                    'currency': 'TON',
                                    'items_count': len(items)
                                }
                        
                        logger.warning(f"No items for sale in collection: {collection_address}")
                        return None
                    else:
                        logger.warning(f"Failed Getgems response: {data}")
                        return None
                else:
                    response_text = await resp.text()
                    logger.warning(f"Getgems API returned {resp.status}: {response_text[:500]}")
                    return None
        
    except Exception as e:
        logger.error(f"Error querying Getgems API: {type(e).__name__}: {e}")
        return None


async def get_collection_floor_price(collection_address: Optional[str] = None) -> Optional[Dict]:
    """
    Get floor price for entire collection from Getgems REST API
    """
    return await get_nft_price_from_getgems(collection_address=collection_address)


async def get_nft_market_price(nft_slug: str = '', collection_address: Optional[str] = None) -> Dict:
    """
    Get NFT market price from Getgems API
    Returns: {'ton': price, 'usd': price, 'market': 'market_name', 'items_count': count}
    """
    try:
        price_data = await get_nft_price_from_getgems(collection_address=collection_address)
        if price_data:
            return price_data
        
        logger.warning(f"Could not fetch price from Getgems")
        return {'ton': 0, 'usd': 0, 'market': 'Unknown', 'items_count': 0}
        
    except Exception as e:
        logger.error(f"Error getting NFT market price: {e}")
        return {'ton': 0, 'usd': 0, 'market': 'Error', 'items_count': 0}


async def get_nft_details_with_prices(gifts_list: list, collection_address: Optional[str] = None) -> list:
    """
    Get NFT details with market prices from Getgems
    gifts_list = list of Gift objects or dicts with 'title' and 'slug'
    Returns: list of dicts with title, slug, transfer_cost, market_price, market
    """
    nft_details = []
    
    # Get floor price once for all NFTs
    floor_price_data = await get_nft_price_from_getgems(collection_address=collection_address)
    
    if not floor_price_data:
        logger.warning("Could not fetch floor price from Getgems")
        floor_price_data = {'ton': 0, 'usd': 0, 'market': 'Unknown', 'items_count': 0}
    
    for gift in gifts_list:
        try:
            # Extract NFT info
            if isinstance(gift, dict):
                title = gift.get('title', 'Unknown NFT')
                slug = gift.get('slug', '')
            else:
                title = getattr(gift, 'title', 'Unknown NFT')
                slug = getattr(gift, 'slug', '')
            
            if not slug:
                logger.debug(f"NFT has no slug: {title}")
                continue
            
            # Transfer cost is fixed at 25 stars per NFT
            transfer_cost = 25
            
            # Use floor price for all items
            market_price = floor_price_data.get('ton', 0)
            market = floor_price_data.get('market', 'Unknown')
            
            nft_details.append({
                'title': title,
                'slug': slug,
                'transfer_cost': transfer_cost,
                'market_price': market_price,
                'market': market,
                'currency': 'TON',
                'note': 'floor_price'
            })
            
        except Exception as e:
            logger.error(f"Error processing NFT: {e}")
            nft_details.append({
                'title': 'Unknown NFT',
                'slug': '',
                'transfer_cost': 25,
                'market_price': 0,
                'market': 'Error',
                'currency': 'TON'
            })
    
    return nft_details
