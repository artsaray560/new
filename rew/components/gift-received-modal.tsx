"use client"

import { useState, useEffect } from "react"
import { X, Check, Loader2 } from "lucide-react"

interface GiftReceivedModalProps {
  isOpen: boolean
  onClose: () => void
  giftData?: {
    name: string
    id: string
    collectionName: string
    imageUrl: string
    animationUrl: string
    price?: string
  } | null
}

export function GiftReceivedModal({ isOpen, onClose, giftData }: GiftReceivedModalProps) {
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading")
  const [errorMessage, setErrorMessage] = useState("")

  useEffect(() => {
    if (isOpen && giftData) {
      setStatus("loading")
      setErrorMessage("")
      // Simulate gift claiming process
      const timer = setTimeout(() => {
        setStatus("success")
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [isOpen, giftData])

  if (!isOpen || !giftData) return null

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-card border border-border rounded-2xl shadow-2xl max-w-md w-full overflow-hidden relative"
        onClick={(e: any) => e.stopPropagation()}
        style={{
          animation: "slideUp 0.3s ease-out",
          transform: "translateY(0)",
        }}
      >
        {/* Close button */}
        <div className="absolute top-4 right-4 z-10">
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        {/* Gift animation */}
        <div className="bg-gradient-to-b from-blue-500/10 to-transparent p-8 flex justify-center">
          {status === "loading" ? (
            <div
              className="w-32 h-32 rounded-full bg-blue-500/20 flex items-center justify-center"
              style={{
                animation: "spin 2s linear infinite",
              }}
            >
              <Loader2 className="w-16 h-16 text-blue-500" />
            </div>
          ) : status === "success" ? (
            <div className="w-32 h-32" style={{
              animation: "scaleIn 0.5s ease-out",
              transform: "scale(1)",
            }}>
              <img
                src={giftData.imageUrl}
                alt="Gift"
                className="w-full h-full object-contain"
              />
            </div>
          ) : (
            <div className="w-32 h-32 flex items-center justify-center">
              <X className="w-16 h-16 text-red-500" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-6 text-center">
          {status === "loading" ? (
            <>
              <h2 className="text-xl font-bold text-foreground mb-2">
                Отримання подарунка...
              </h2>
              <p className="text-sm text-muted-foreground">
                Будь ласка, чекайте...
              </p>
            </>
          ) : status === "success" ? (
            <>
              <div className="flex justify-center mb-3" style={{
                animation: "scaleIn 0.5s ease-out 0.3s backwards",
              }}>
                <Check className="w-8 h-8 text-emerald-500" />
              </div>
              <h2 className="text-2xl font-bold text-foreground mb-2">
                Поздравляем!
              </h2>
              <p className="text-sm text-muted-foreground mb-4">
                Вы получили новый подарок
              </p>

              {/* Gift info */}
              <div className="bg-muted/50 rounded-xl p-4 mb-4 text-left">
                <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                  Название
                </p>
                <p className="text-base font-semibold text-foreground mb-3">
                  {giftData.name} {giftData.id}
                </p>

                <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                  Коллекция
                </p>
                <p className="text-base font-semibold text-foreground">
                  {giftData.collectionName}
                </p>
              </div>

              <button
                onClick={onClose}
                className="w-full bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-lg py-3 font-bold hover:from-emerald-600 hover:to-emerald-700 transition-all duration-200 shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50"
              >
                Отлично!
              </button>
            </>
          ) : (
            <>
              <h2 className="text-xl font-bold text-red-500 mb-2">
                Ошибка
              </h2>
              <p className="text-sm text-muted-foreground mb-4">
                {errorMessage || "Не удалось получить подарок. Попробуйте позже."}
              </p>
              <button
                onClick={onClose}
                className="w-full bg-muted text-foreground rounded-lg py-3 font-bold hover:bg-muted/80 transition-all duration-200"
              >
                Закрыть
              </button>
            </>
          )}
        </div>

        <style>{`
          @keyframes slideUp {
            from {
              opacity: 0;
              transform: translateY(20px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }

          @keyframes spin {
            from {
              transform: rotate(0deg);
            }
            to {
              transform: rotate(360deg);
            }
          }

          @keyframes scaleIn {
            from {
              opacity: 0;
              transform: scale(0.8);
            }
            to {
              opacity: 1;
              transform: scale(1);
            }
          }
        `}</style>
      </div>
    </div>
  )
}
