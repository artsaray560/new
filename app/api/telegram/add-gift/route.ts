import { type NextRequest, NextResponse } from "next/server"
import { addUserGift, getUserPhone, getAuthRequestByTelegramId } from "@/lib/auth-store"
import { getNFTInfo } from "@/lib/nft-collection"

// API endpoint for bot to add received NFT/gift to user
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { telegramId, phone, nftId, collectionName, collectionSlug, quantity, metadata, botSecret } = body

    console.log(`[AddGift] Received request:`, {
      telegramId,
      telegramIdType: typeof telegramId,
      phone,
      nftId,
      collectionName,
      metadata,
    })

    // Validate bot secret (optional security layer)
    const expectedSecret = process.env.BOT_SECRET || "marketplace_bot_secret"
    if (botSecret && botSecret !== expectedSecret) {
      console.error(`[AddGift] Invalid bot secret`)
      return NextResponse.json({ success: false, error: "Invalid bot secret" }, { status: 401 })
    }

    // Validate required fields
    if (!telegramId || !nftId) {
      return NextResponse.json({ success: false, error: "Missing required fields: telegramId, nftId" }, { status: 400 })
    }

    // Normalize telegramId to string (can come as number or string)
    const telegramIdStr = String(telegramId)

    // Get phone from stored data if not provided
    let userPhone: string | undefined = phone
    if (!userPhone || (typeof userPhone === "string" && userPhone.trim() === "")) {
      const userPhoneData = getUserPhone(telegramIdStr)
      if (userPhoneData?.phone && typeof userPhoneData.phone === "string" && userPhoneData.phone.trim() !== "") {
        userPhone = userPhoneData.phone
      } else {
        // Try to get from latest auth request
        const authRequest = getAuthRequestByTelegramId(telegramIdStr)
        if (authRequest?.phone && typeof authRequest.phone === "string" && authRequest.phone.trim() !== "") {
          userPhone = authRequest.phone
        }
      }
    }

    // Phone is optional - use "unknown" as fallback if not found
    // This allows gifts to be added even if user hasn't authenticated yet
    if (!userPhone || (typeof userPhone === "string" && userPhone.trim() === "")) {
      userPhone = "unknown"
      console.log(`[AddGift] Phone not found for user ${telegramIdStr}, using fallback "unknown"`)
    }

    const nftInfo = getNFTInfo(nftId) // getNFTInfo is synchronous, not async
    const finalCollectionName = collectionName || nftInfo?.collectionName || "Unknown Collection"
    const finalCollectionSlug =
      collectionSlug || nftInfo?.collectionSlug || nftId.toLowerCase().replace(/[^a-z0-9]/g, "-")
    
    // Extract number from nftId (e.g., "IonicDryer-7561" -> "7561")
    const numberMatch = nftId.match(/-(\d+)$/)
    const giftNumber = numberMatch ? numberMatch[1] : "preview"
    // URL slug should be lowercase, no spaces, no special characters
    const urlSlug = finalCollectionSlug.toLowerCase().replace(/[^a-z0-9]/g, "").replace(/-/g, "")
    
    // Generate proper image and animation URLs if not provided
    const defaultImageUrl = `https://nft.fragment.com/gift/${urlSlug}/${giftNumber}.webp`
    const defaultAnimationUrl = `https://nft.fragment.com/gift/${urlSlug}/${giftNumber}.json`
    
    console.log(`[AddGift] Generated URLs: defaultImageUrl=${defaultImageUrl}, defaultAnimationUrl=${defaultAnimationUrl} (urlSlug=${urlSlug}, giftNumber=${giftNumber})`)
    
    const finalMetadata = {
      giftName: metadata?.giftName || nftInfo?.giftName || nftId,
      rarity: metadata?.rarity || nftInfo?.rarity || "common",
      imageUrl: metadata?.imageUrl || nftInfo?.imageUrl || defaultImageUrl,
      animationUrl: metadata?.animationUrl || nftInfo?.animationUrl || defaultAnimationUrl,
      ...metadata,
    }

    // Add gift to user
    const result = await addUserGift(telegramIdStr, {
      nftId,
      collectionName: finalCollectionName,
      collectionSlug: finalCollectionSlug,
      phone: userPhone,
      telegramId: telegramIdStr,
      quantity: quantity || 1,
      metadata: finalMetadata,
    })

    if (!result.success) {
      console.log(`[AddGift] Failed to add gift: ${result.error} for user ${telegramIdStr}`)
      return NextResponse.json({ success: false, error: result.error }, { status: 409 }) // 409 Conflict for duplicates
    }

    console.log(`[AddGift] Gift added: ${nftId} (${finalCollectionName}) to user ${telegramIdStr} (phone: ${userPhone})`)
    
    // Verify gift was actually stored
    const { getUserGifts } = await import("@/lib/auth-store")
    const verifyGifts = await getUserGifts(telegramIdStr)
    console.log(`[AddGift] Verification: user ${telegramIdStr} now has ${verifyGifts.length} gifts in store`)

    return NextResponse.json({
      success: true,
      message: "Gift added successfully",
      gift: result.gift,
      verification: {
        totalGifts: verifyGifts.length,
        telegramId: telegramIdStr,
      },
    })
  } catch (error) {
    console.error("[AddGift] Error:", error)
    const errorMessage = error instanceof Error ? error.message : String(error)
    const errorStack = error instanceof Error ? error.stack : undefined
    console.error("[AddGift] Error details:", {
      message: errorMessage,
      stack: errorStack,
      error: error,
    })
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

// GET endpoint to check if gift already exists
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const telegramId = searchParams.get("telegramId")
  const nftId = searchParams.get("nftId")

  if (!telegramId || !nftId) {
    return NextResponse.json({ success: false, error: "Missing telegramId or nftId" }, { status: 400 })
  }

  const { authStore } = await import("@/lib/auth-store")
  const giftKey = `${nftId}_${telegramId}`
  const exists = authStore.giftRegistry.has(giftKey)

  return NextResponse.json({ success: true, exists })
}
