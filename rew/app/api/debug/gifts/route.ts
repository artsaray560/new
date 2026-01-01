// @ts-ignore - Next.js types are available at runtime
import { type NextRequest, NextResponse } from "next/server"
import { authStore } from "@/lib/auth-store"

// Debug endpoint to check all gifts in store
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const checkUserId = searchParams.get("userId")
    
    const allGifts: Record<string, any[]> = {}
    const allKeys: string[] = []

    // Get all user gifts
    for (const [telegramId, gifts] of authStore.userGifts.entries()) {
      allGifts[telegramId] = gifts
      allKeys.push(telegramId)
    }

    // Get all gift registry entries
    const registryEntries = Array.from(authStore.giftRegistry)
    
    const totalGifts = Object.values(allGifts).reduce((sum, gifts) => sum + gifts.length, 0)
    
    // Check specific user if provided
    let userCheck: any = null
    if (checkUserId) {
      const normalizedId = String(checkUserId)
      const userGifts = allGifts[normalizedId] || []
      const exactMatch = allKeys.includes(normalizedId)
      const similarKeys = allKeys.filter(k => String(k) === String(checkUserId))
      
      userCheck = {
        requestedId: checkUserId,
        normalizedId,
        exactMatch,
        similarKeys,
        foundGifts: userGifts.length,
        gifts: userGifts,
      }
    }

    return NextResponse.json({
      success: true,
      timestamp: new Date().toISOString(),
      // @ts-ignore - process is available in Node.js runtime
      instance: process.env.VERCEL_REGION || "unknown",
      totalUsers: allKeys.length,
      allKeys,
      giftsByUser: allGifts,
      registryEntries,
      registrySize: registryEntries.length,
      totalGifts,
      userCheck,
      note: "⚠️ На Vercel serverless functions працюють на різних instances. Дані можуть бути втрачені між викликами.",
    })
  } catch (error) {
    console.error("[DebugGifts] Error:", error)
    return NextResponse.json({ success: false, error: String(error) }, { status: 500 })
  }
}

