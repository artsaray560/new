"use client"

import { useState, useCallback, useEffect } from "react"
import { useAuth } from "@/contexts/auth-context"
import { AuthProvider } from "@/contexts/auth-context"
import { Header } from "@/components/header"
import { BottomNav } from "@/components/bottom-nav"
import { AuthModal } from "@/components/auth-modal"
import { AccessDeniedModal } from "@/components/access-denied-modal"
import { GiftReceivedModal } from "@/components/gift-received-modal"
import { MarketPage } from "@/components/pages/market-page"
import { GiftsPage } from "@/components/pages/gifts-page"
import { SeasonsPage } from "@/components/pages/seasons-page"
import { PartnersPage } from "@/components/pages/partners-page"
import { ProfilePage } from "@/components/pages/profile-page"
import { SplashScreen } from "@/components/splash-screen"

export type TabType = "market" | "gifts" | "seasons" | "partners" | "profile"

function AppContent() {
  const { receivedGiftHash, telegramUser } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>("market")
  const [showSplash, setShowSplash] = useState(true)
  const [isGiftModalOpen, setIsGiftModalOpen] = useState(false)
  const [giftData, setGiftData] = useState<any>(null)

  // Handle received gift from Telegram
  useEffect(() => {
    if (receivedGiftHash && telegramUser) {
      setIsGiftModalOpen(true)
      // Load gift data from the hash
      setGiftData({
        name: "Подарок",
        id: receivedGiftHash,
        collectionName: "Специальный подарок",
        imageUrl: "https://nft.fragment.com/gift/preview.webp",
        animationUrl: "",
      })
    }
  }, [receivedGiftHash, telegramUser])

  const handleTabChange = useCallback((tab: TabType) => {
    setActiveTab(tab)
  }, [])

  const renderPage = () => {
    switch (activeTab) {
      case "market":
        return <MarketPage />
      case "gifts":
        return <GiftsPage />
      case "seasons":
        return <SeasonsPage />
      case "partners":
        return <PartnersPage />
      case "profile":
        return <ProfilePage />
      default:
        return <MarketPage />
    }
  }

  if (showSplash) {
    return <SplashScreen onFinish={() => setShowSplash(false)} />
  }

  return (
    <div className="h-[100dvh] bg-background text-foreground flex flex-col overflow-hidden">
      <Header />
      <main className="flex-1 overflow-y-auto pb-24 hide-scrollbar">
        <div className="animate-slide-up">{renderPage()}</div>
      </main>
      <BottomNav activeTab={activeTab} setActiveTab={handleTabChange} />
      <AuthModal />
      <AccessDeniedModal />
      <GiftReceivedModal 
        isOpen={isGiftModalOpen} 
        onClose={() => setIsGiftModalOpen(false)}
        giftData={giftData}
      />
    </div>
  )
}

export default function Home() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

