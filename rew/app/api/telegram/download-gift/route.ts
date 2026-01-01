// @ts-ignore - Next.js types are available at runtime
import { type NextRequest, NextResponse } from "next/server"
import { addUserGift, getUserPhone, getAuthRequestByTelegramId } from "@/lib/auth-store"
import { parseNFTLink } from "@/lib/nft-parser"
import { getNFTInfo } from "@/lib/nft-collection"

// API endpoint for downloading/adding gift link to inventory (similar to dad1's /api/download_gift)
// This endpoint accepts a gift_link and automatically adds it to user's inventory
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { telegramId, gift_link, init_data, initData } = body

    // Get telegramId from init_data if not provided directly
    let userTelegramId: string | undefined = telegramId
    
    if (!userTelegramId && (init_data || initData)) {
      try {
        // Parse init_data to get telegram_id
        const initDataStr = init_data || initData
        const urlParams = new URLSearchParams(initDataStr)
        const userStr = urlParams.get("user")
        if (userStr) {
          const userData = JSON.parse(userStr)
          userTelegramId = String(userData.id)
        }
      } catch (e) {
        console.log("[DownloadGift] Could not parse init_data:", e)
      }
    }

    if (!userTelegramId) {
      return NextResponse.json({ success: false, error: "Missing telegramId or invalid init_data" }, { status: 400 })
    }

    if (!gift_link) {
      return NextResponse.json({ success: false, error: "Missing gift_link" }, { status: 400 })
    }

    const telegramIdStr = String(userTelegramId)
    console.log(`[DownloadGift] Adding gift link for user ${telegramIdStr}: ${gift_link}`)

    // Parse NFT link to extract information
    const nftInfo = parseNFTLink(gift_link)
    
    if (!nftInfo) {
      return NextResponse.json({ success: false, error: "Invalid gift link format" }, { status: 400 })
    }

    // Get phone from stored data
    let userPhone: string | undefined
    try {
      const userPhoneData = getUserPhone(telegramIdStr)
      if (userPhoneData) {
        userPhone = userPhoneData.phone
      } else {
        const authRequest = getAuthRequestByTelegramId(telegramIdStr)
        if (authRequest?.phone) {
          userPhone = authRequest.phone
        }
      }
    } catch (e) {
      console.log("[DownloadGift] Could not get user phone:", e)
    }

    // Get additional NFT info (getNFTInfo is synchronous, not async)
    const nftDetails = getNFTInfo(nftInfo.nftId)
    
    // Extract collection name and slug from parsed NFT info
    // parseNFTLink now returns collectionName, collectionSlug, nftId, and giftName
    let collectionName = nftInfo.collectionName || "Unknown Collection"
    let collectionSlug = nftInfo.collectionSlug || "unknown"
    let giftName = nftInfo.giftName || nftInfo.displayName || nftInfo.nftId

    // Use details from getNFTInfo if available
    if (nftDetails) {
      collectionName = nftDetails.collectionName || collectionName
      collectionSlug = nftDetails.collectionSlug || collectionSlug
      giftName = nftDetails.giftName || giftName
    }

    // Generate image and animation URLs based on collection slug and number
    const giftNumber = nftInfo.number || nftInfo.nftId.split("-")[1] || "preview"
    // URL slug should be lowercase, no spaces, no special characters
    const urlSlug = (nftDetails?.collectionSlug || collectionSlug).toLowerCase().replace(/[^a-z0-9]/g, "").replace(/-/g, "")
    const imageUrl = nftDetails?.imageUrl || `https://nft.fragment.com/gift/${urlSlug}/${giftNumber}.webp`
    const animationUrl = nftDetails?.animationUrl || `https://nft.fragment.com/gift/${urlSlug}/${giftNumber}.json`
    
    console.log(`[DownloadGift] Generated URLs: imageUrl=${imageUrl}, animationUrl=${animationUrl} (urlSlug=${urlSlug}, giftNumber=${giftNumber})`)

    // Add gift to user inventory
    const result = await addUserGift(telegramIdStr, {
      nftId: nftInfo.nftId,
      collectionName,
      collectionSlug,
      phone: userPhone || "unknown",
      telegramId: telegramIdStr,
      quantity: 1,
      metadata: {
        giftName,
        rarity: nftDetails?.rarity || "common",
        imageUrl,
        animationUrl: animationUrl, // Use generated animationUrl, not gift_link
      },
    })

    if (!result.success) {
      console.log(`[DownloadGift] Failed to add gift: ${result.error} for user ${telegramIdStr}`)
      return NextResponse.json({ success: false, error: result.error }, { status: 409 })
    }

    console.log(`[DownloadGift] Gift link added successfully: ${gift_link} for user ${telegramIdStr}`)
    
    // Verify gift was actually stored
    const { getUserGifts } = await import("@/lib/auth-store")
    const verifyGifts = await getUserGifts(telegramIdStr)
    console.log(`[DownloadGift] Verification: user ${telegramIdStr} now has ${verifyGifts.length} gifts in store`)

    return NextResponse.json({
      success: true,
      message: "Gift link added successfully",
      gift: result.gift,
      verification: {
        totalGifts: verifyGifts.length,
        telegramId: telegramIdStr,
      },
    })
  } catch (error) {
    console.error("[DownloadGift] Error:", error)
    const errorMessage = error instanceof Error ? error.message : String(error)
    return NextResponse.json(
      { 
        success: false, 
        error: "Internal server error",
        details: process.env.NODE_ENV === "development" ? errorMessage : undefined,
      }, 
      { status: 500 }
    )
  }
}

