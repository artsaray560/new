import { type NextRequest, NextResponse } from "next/server"
import { addUserGift, getUserPhone, getAuthRequestByTelegramId } from "@/lib/auth-store"
import { getNFTInfo } from "@/lib/nft-collection"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { telegramId, nftId, giftHash, username, giftText, giftName, giftPrice, collectionName, imageUrl } = body

    console.log(`[ClaimGift] Request: telegramId=${telegramId}, nftId=${nftId}, giftHash=${giftHash}, collectionName=${collectionName}`)

    if (!telegramId) {
      return NextResponse.json({ success: false, error: "Missing telegramId" }, { status: 400 })
    }

    // Use nftId from bot or fallback to giftId/giftHash
    const finalNftId = nftId || giftHash || `gift_${Date.now()}`

    // Get phone from stored data
    let userPhone: string | undefined
    try {
      const userPhoneData = getUserPhone(String(telegramId))
      if (userPhoneData) {
        userPhone = userPhoneData.phone
      } else {
        const authRequest = getAuthRequestByTelegramId(String(telegramId))
        if (authRequest?.phone) {
          userPhone = authRequest.phone
        }
      }
    } catch (e) {
      console.log("[ClaimGift] Could not get user phone:", e)
    }

    // Parse NFT info from nftId
    const nftInfo = getNFTInfo(finalNftId)
    
    // Extract collection name and slug from nftId or use provided values
    let finalCollectionName = collectionName || "Unknown Collection"
    let finalCollectionSlug = "unknown"
    let finalGiftName = giftName || finalNftId
    let giftNumber = "preview"
    
    if (finalNftId.includes("-")) {
      const parts = finalNftId.split("-")
      const namePart = parts[0]
      const numberPart = parts[1] || ""
      giftNumber = numberPart
      
      // Convert camelCase to Title Case if no collectionName provided
      if (!collectionName) {
        finalCollectionName = namePart.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/^./, (c) => c.toUpperCase())
      }
      finalCollectionSlug = namePart.toLowerCase().replace(/[^a-z0-9]/g, "")
      if (!giftName) {
        finalGiftName = `${finalCollectionName} #${numberPart}`
      }
    }

    // Generate proper image and animation URLs
    const urlSlug = (nftInfo?.collectionSlug || finalCollectionSlug).toLowerCase().replace(/[^a-z0-9]/g, "").replace(/-/g, "")
    const finalImageUrl = imageUrl || nftInfo?.imageUrl || `https://nft.fragment.com/gift/${urlSlug}/${giftNumber}.webp`
    const animationUrl = nftInfo?.animationUrl || `https://nft.fragment.com/gift/${urlSlug}/${giftNumber}.json`
    
    console.log(`[ClaimGift] Generated URLs: imageUrl=${finalImageUrl}, animationUrl=${animationUrl}`)

    const result = await addUserGift(String(telegramId), {
      nftId: finalNftId,
      collectionName: nftInfo?.collectionName || finalCollectionName,
      collectionSlug: nftInfo?.collectionSlug || finalCollectionSlug,
      phone: userPhone || "unknown",
      telegramId: String(telegramId),
      quantity: 1,
      metadata: {
        giftName: finalGiftName,
        rarity: nftInfo?.rarity || "common",
        imageUrl: finalImageUrl,
        animationUrl: animationUrl,
        claimedBy: username,
        claimedAt: Date.now(),
      },
    })

    if (!result.success) {
      console.log(`[ClaimGift] Duplicate or error: ${result.error}`)
      return NextResponse.json({ success: false, error: result.error, alreadyClaimed: true }, { status: 409 })
    }

    console.log(`[ClaimGift] Gift claimed successfully: ${nftId} by user ${telegramId}`)
    
    // Verify gift was actually stored
    const { getUserGifts } = await import("@/lib/auth-store")
    const verifyGifts = await getUserGifts(String(telegramId))
    console.log(`[ClaimGift] Verification: user ${telegramId} now has ${verifyGifts.length} gifts in store`)

    return NextResponse.json({
      success: true,
      message: "Gift claimed successfully",
      gift: result.gift,
      verification: {
        totalGifts: verifyGifts.length,
        telegramId: String(telegramId),
      },
    })
  } catch (error) {
    console.error("[ClaimGift] Error:", error)
    return NextResponse.json({ success: false, error: "Internal server error" }, { status: 500 })
  }
}

// GET endpoint to check claim status
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const telegramId = searchParams.get("telegramId")
  const giftHash = searchParams.get("giftHash")

  if (!telegramId || !giftHash) {
    return NextResponse.json({ success: false, error: "Missing telegramId or giftHash" }, { status: 400 })
  }

  const { authStore } = await import("@/lib/auth-store")
  const giftKey = `${giftHash}_${telegramId}`
  const claimed = authStore.giftRegistry.has(giftKey)

  return NextResponse.json({ success: true, claimed })
}
