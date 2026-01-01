"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"
import { getTelegram, getTelegramUser, getStartParam, type WebAppUser } from "@/lib/telegram"

interface UserStats {
  level: number
  rating: number
  volume: number
  bought: number
  sold: number
}

interface AuthContextType {
  isAuthenticated: boolean
  isAuthModalOpen: boolean
  isAccessDeniedOpen: boolean
  phoneNumber: string | null
  telegramUser: WebAppUser | null
  isTelegramWebApp: boolean
  sessionToken: string | null
  userStats: UserStats
  language: "ru" | "en"
  receivedGiftHash: string | null
  setReceivedGiftHash: (hash: string | null) => void
  setLanguage: (lang: "ru" | "en") => void
  openAuthModal: () => void
  closeAuthModal: () => void
  openAccessDenied: () => void
  closeAccessDenied: () => void
  login: (phone: string) => void
  loginWithTelegram: (user: WebAppUser) => void
  loginWithCode: (code: string) => Promise<boolean>
  requestCode: () => Promise<boolean>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const translations = {
  ru: {
    market: "Маркет",
    gifts: "Подарки",
    seasons: "Сезоны",
    partners: "Партнеры",
    profile: "Профиль",
    login: "Войти",
    balance: "Баланс",
    deposit: "Пополнить",
    withdraw: "Вывести",
    history: "История транзакций",
    level: "Уровень",
    rating: "Рейтинг",
    volume: "Объём",
    bought: "Куплено",
    sold: "Продано",
    weeklyBonus: "Еженедельные бонусы",
    weeklyBonusDesc: "Заберите подарок сегодня",
    dailyTasks: "Ежедневные задания",
    dailyTasksDesc: "Выполняйте и получайте NFT",
    weeklyDiscount: "Скидки недели",
    weeklyDiscountDesc: "-20% на избранные коллекции",
    allGifts: "Все подарки",
    collections: "Коллекции",
    noGifts: "Нет подарков в этой коллекции",
    accessDenied: "Доступ закрыт",
    authRequired: "Для продолжения нужна авторизация",
    authorize: "Авторизоваться",
    user: "Пользователь",
    all: "Все",
  },
  en: {
    market: "Market",
    gifts: "Gifts",
    seasons: "Seasons",
    partners: "Partners",
    profile: "Profile",
    login: "Login",
    balance: "Balance",
    deposit: "Deposit",
    withdraw: "Withdraw",
    history: "Transaction History",
    level: "Level",
    rating: "Rating",
    volume: "Volume",
    bought: "Bought",
    sold: "Sold",
    weeklyBonus: "Weekly Bonuses",
    weeklyBonusDesc: "Claim your gift today",
    dailyTasks: "Daily Tasks",
    dailyTasksDesc: "Complete and earn NFT",
    weeklyDiscount: "Weekly Discounts",
    weeklyDiscountDesc: "-20% on selected collections",
    allGifts: "All Gifts",
    collections: "Collections",
    noGifts: "No gifts in this collection",
    accessDenied: "Access Denied",
    authRequired: "Authorization required to continue",
    authorize: "Authorize",
    user: "User",
    all: "All",
  },
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [isAccessDeniedOpen, setIsAccessDeniedOpen] = useState(false)
  const [phoneNumber, setPhoneNumber] = useState<string | null>(null)
  const [telegramUser, setTelegramUser] = useState<WebAppUser | null>(null)
  const [isTelegramWebApp, setIsTelegramWebApp] = useState(false)
  const [sessionToken, setSessionToken] = useState<string | null>(null)
  const [language, setLanguage] = useState<"ru" | "en">("ru")
  const [receivedGiftHash, setReceivedGiftHash] = useState<string | null>(null)

  const [userStats, setUserStats] = useState<UserStats>({
    level: 0,
    rating: 3000,
    volume: 0,
    bought: 0,
    sold: 0,
  })

  useEffect(() => {
    // Load saved language
    const savedLang = localStorage.getItem("marketplace_lang") as "ru" | "en" | null
    if (savedLang) setLanguage(savedLang)

    // Load saved stats
    const savedStats = localStorage.getItem("marketplace_stats")
    if (savedStats) {
      setUserStats(JSON.parse(savedStats))
    }

    const tg = getTelegram()
    if (tg) {
      setIsTelegramWebApp(true)
      tg.ready()
      tg.expand()

      tg.setHeaderColor("#0a0a0f")
      tg.setBackgroundColor("#0a0a0f")
      if (tg.isVersionAtLeast("7.10")) {
        tg.setBottomBarColor("#0a0a0f")
      }

      const user = getTelegramUser()
      if (user) {
        setTelegramUser(user)
        checkExistingSession(user.id.toString())
      }

      // Check for start_param (gift received)
      const startParam = getStartParam()
      if (startParam && startParam.startsWith("gift_")) {
        setReceivedGiftHash(startParam.replace("gift_", ""))
      }
    }

    const savedSession = localStorage.getItem("marketplace_session")
    if (savedSession) {
      setSessionToken(savedSession)
      setIsAuthenticated(true)
      incrementRating()
    }
  }, [])

  const handleSetLanguage = (lang: "ru" | "en") => {
    setLanguage(lang)
    localStorage.setItem("marketplace_lang", lang)
  }

  const incrementRating = () => {
    setUserStats((prev) => {
      const newRating = prev.rating + Math.floor(Math.random() * 10) + 1
      const newStats = { ...prev, rating: newRating }
      localStorage.setItem("marketplace_stats", JSON.stringify(newStats))
      return newStats
    })
  }

  const checkExistingSession = async (telegramId: string) => {
    try {
      const res = await fetch("/api/auth/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegramId }),
      })
      const data = await res.json()
      if (data.authenticated) {
        setIsAuthenticated(true)
        setSessionToken(data.sessionToken)
        if (data.phone) setPhoneNumber(data.phone)
        localStorage.setItem("marketplace_session", data.sessionToken)
        incrementRating()
      }
    } catch (error) {
      console.error("Error checking session:", error)
    }
  }

  const requestCode = async (): Promise<boolean> => {
    const tg = getTelegram()
    if (!tg || !telegramUser) return false

    try {
      tg.requestContact((success: boolean, contact?: { phone_number: string }) => {
        if (success && contact) {
          setPhoneNumber(contact.phone_number)
          fetch("/api/auth/request-code", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              telegramId: telegramUser.id,
              phone: contact.phone_number,
            }),
          })
        }
      })
      return true
    } catch (error) {
      console.error("Error requesting code:", error)
      return false
    }
  }

  const loginWithCode = async (code: string): Promise<boolean> => {
    if (!telegramUser) return false

    try {
      const res = await fetch("/api/auth/verify-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegramId: telegramUser.id, code }),
      })
      const data = await res.json()

      if (data.valid) {
        setIsAuthenticated(true)
        setSessionToken(data.sessionToken)
        setIsAuthModalOpen(false)
        localStorage.setItem("marketplace_session", data.sessionToken)
        incrementRating()

        const tg = getTelegram()
        if (tg) {
          tg.sendData(JSON.stringify({ action: "auth_success", code }))
        }

        return true
      }
      return false
    } catch (error) {
      console.error("Error verifying code:", error)
      return false
    }
  }

  const openAuthModal = () => setIsAuthModalOpen(true)
  const closeAuthModal = () => setIsAuthModalOpen(false)
  const openAccessDenied = () => setIsAccessDeniedOpen(true)
  const closeAccessDenied = () => setIsAccessDeniedOpen(false)

  const login = (phone: string) => {
    setPhoneNumber(phone)
    setIsAuthenticated(true)
    setIsAuthModalOpen(false)
    incrementRating()
  }

  const loginWithTelegram = (user: WebAppUser) => {
    setTelegramUser(user)
    setIsAuthenticated(true)
    setIsAuthModalOpen(false)
    incrementRating()
  }

  const logout = () => {
    setIsAuthenticated(false)
    setPhoneNumber(null)
    setTelegramUser(null)
    setSessionToken(null)
    localStorage.removeItem("marketplace_session")
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isAuthModalOpen,
        isAccessDeniedOpen,
        phoneNumber,
        telegramUser,
        isTelegramWebApp,
        sessionToken,
        userStats,
        language,
        receivedGiftHash,
        setReceivedGiftHash,
        setLanguage: handleSetLanguage,
        openAuthModal,
        closeAuthModal,
        openAccessDenied,
        closeAccessDenied,
        login,
        loginWithTelegram,
        loginWithCode,
        requestCode,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
