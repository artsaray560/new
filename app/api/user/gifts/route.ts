import { type NextRequest, NextResponse } from "next/server"
import { getUserGifts, getUserGiftsByPhone, getTotalGiftsCount } from "@/lib/auth-store"

// GET user's gifts
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const telegramId = searchParams.get("telegramId")
  const phone = searchParams.get("phone")

  console.log(`[GetGifts] === Fetching Gifts ===`)
  console.log(`[GetGifts] Query params:`, { telegramId, phone })

  if (!telegramId && !phone) {
    return NextResponse.json({ success: false, error: "Missing telegramId or phone" }, { status: 400 })
  }

  let gifts = []
  let totalCount = 0
  let telegramIdStr: string | undefined = undefined

  if (telegramId) {
    // Normalize telegramId to string (can come as number or string from query params)
    telegramIdStr = String(telegramId)
    console.log(`[GetGifts] Fetching gifts for telegramId: ${telegramIdStr}`)
    gifts = await getUserGifts(telegramIdStr)
    totalCount = await getTotalGiftsCount(telegramIdStr)
    console.log(`[GetGifts] Found ${gifts.length} gifts for user ${telegramIdStr}`)
  } else if (phone) {
    gifts = await getUserGiftsByPhone(phone)
    totalCount = gifts.reduce((total: number, gift: any) => total + (gift.quantity || 1), 0)
  }

  return NextResponse.json({
    success: true,
    gifts,
    totalCount,
    debug: telegramId && telegramIdStr ? {
      requestedId: telegramId,
      normalizedId: telegramIdStr,
      foundGifts: gifts.length,
    } : undefined,
  })
}
