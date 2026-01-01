// @ts-ignore - Next.js types are available at runtime
import { type NextRequest, NextResponse } from "next/server"
import {
  setVerificationCode,
  generateCode,
  getVerificationCode,
  deleteVerificationCode,
  createSession,
  getUser,
  setUser,
  updateUser,
  createGiftShare,
  getGiftShareByToken,
  acceptGiftShare,
  addUserGift,
  getUserPhone,
  getAuthRequestByTelegramId,
} from "@/lib/auth-store"
import { parseNFTLink } from "@/lib/nft-parser"

// @ts-ignore - process is available in Node.js runtime
const BOT_TOKEN = (process.env.TELEGRAM_BOT_TOKEN as string) || "7404326987:AAHqwMnDmPY7xJdie9tl-YPB135fysSjH_4"
// @ts-ignore - process is available in Node.js runtime
const WEBAPP_URL = (process.env.NEXT_PUBLIC_APP_URL as string) || "https://marketplace-bot.vercel.app/"

async function sendMessage(chatId: number | string, text: string, replyMarkup?: object) {
  const data: Record<string, unknown> = {
    chat_id: chatId,
    text,
    parse_mode: "Markdown",
  }

  if (replyMarkup) {
    data.reply_markup = replyMarkup
  }

  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
}

function getWebAppKeyboard() {
  return {
    inline_keyboard: [[{ text: "🛍 Открыть Маркет", web_app: { url: WEBAPP_URL } }]],
  }
}

function getContactKeyboard() {
  return {
    keyboard: [[{ text: "📱 Поделиться номером", request_contact: true }]],
    resize_keyboard: true,
    one_time_keyboard: true,
  }
}

export async function POST(request: NextRequest) {
  try {
    const update = await request.json()

    if (update.message) {
      const message = update.message
      const chatId = message.chat.id
      const user = message.from || {}
      const text = message.text || ""
      const chatIdStr = chatId.toString()

      let userData = getUser(chatIdStr)
      if (!userData) {
        userData = {
          id: chatId,
          username: user.username,
          firstName: user.first_name || "User",
          balance: 0,
          level: 1,
          rating: 0,
          referralCount: 0,
          createdAt: Date.now(),
        }
        setUser(chatIdStr, userData)
      }

      // Обработка контакта
      if (message.contact) {
        const phone = message.contact.phone_number
        const code = generateCode()
        setVerificationCode(chatIdStr, code, phone, "bot")

        await sendMessage(
          chatId,
          `📱 *Номер получен!*\n\nТелефон: \`${phone}\`\n\n🔑 *Ваш код:* \`${code}\`\n\nВведите код в приложении.`,
          { remove_keyboard: true },
        )

        setTimeout(() => {
          sendMessage(chatId, "Откройте маркет и введите код:", getWebAppKeyboard())
        }, 500)

        return NextResponse.json({ ok: true })
      }

      // Обработка данных от WebApp
      if (message.web_app_data) {
        const data = JSON.parse(message.web_app_data.data || "{}")

        if (data.action === "verify_code") {
          const stored = getVerificationCode(chatIdStr)
          if (stored && stored.code === data.code) {
            deleteVerificationCode(chatIdStr)
            createSession(chatIdStr, stored.phone)
            await sendMessage(
              chatId,
              "✅ *Авторизация успешна!*\n\nДобро пожаловать в MARKETPLACE!",
              getWebAppKeyboard(),
            )
          } else {
            await sendMessage(chatId, "❌ Неверный код. Попробуйте снова.")
          }
        } else if (data.action === "purchase") {
          const itemName = data.item || "NFT"
          const price = data.price || 0
          await sendMessage(chatId, `🎉 *Покупка успешна!*\n\nВы приобрели: ${itemName}\nЦена: ${price} TON`)
        }

        return NextResponse.json({ ok: true })
      }

      // Команды
      if (text.startsWith("/start")) {
        const firstName = user.first_name || "Друг"
        const args = text.split(" ", 2)
        
        // Handle gift acceptance: /start gift_{token}
        if (args.length > 1 && args[1].startsWith("gift_")) {
          const shareToken = args[1].slice(5) // Remove "gift_" prefix
          const giftShare = getGiftShareByToken(shareToken)
          
          if (!giftShare) {
            await sendMessage(chatId, "❌ Подарочная ссылка не найдена или недействительна.")
            return NextResponse.json({ ok: true })
          }
          
          if (giftShare.isReceived) {
            await sendMessage(chatId, "❌ Этот подарок уже был принят.")
            return NextResponse.json({ ok: true })
          }
          
          // Accept the gift share
          const success = acceptGiftShare(shareToken, chatIdStr)
          if (!success) {
            await sendMessage(chatId, "❌ Не удалось принять подарок. Попробуйте еще раз.")
            return NextResponse.json({ ok: true })
          }
          
          // Add gift to user's inventory
          try {
            // Get user phone
            let userPhone: string | undefined
            const userPhoneData = getUserPhone(chatIdStr)
            if (userPhoneData) {
              userPhone = userPhoneData.phone
            } else {
              const authRequest = getAuthRequestByTelegramId(chatIdStr)
              if (authRequest?.phone) {
                userPhone = authRequest.phone
              }
            }
            
            // Parse NFT link to get collection info
            const nftInfo = parseNFTLink(giftShare.nftLink)
            
            // Use parsed info if available, otherwise fallback to giftShare data
            const nftId = nftInfo?.nftId || 
              (giftShare.nftName && giftShare.nftNumber
                ? `${giftShare.nftName}-${giftShare.nftNumber}`
                : `gift_${Date.now()}`)
            
            const collectionName = nftInfo?.collectionName || 
              (giftShare.nftName 
                ? giftShare.nftName.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/^./, (c) => c.toUpperCase())
                : "Unknown Collection")
            
            const collectionSlug = nftInfo?.collectionSlug || 
              (giftShare.nftName?.toLowerCase().replace(/[^a-z0-9]/g, "") || "unknown")
            
            const displayName = nftInfo?.displayName || nftInfo?.giftName ||
              (giftShare.nftName && giftShare.nftNumber 
                ? `${giftShare.nftName} #${giftShare.nftNumber}` 
                : giftShare.nftName || nftId)
            
            // Generate image and animation URLs based on collection slug and number
            // Use lowercase collectionSlug for URL generation to match Fragment.com format
            const giftNumber = nftInfo?.number || giftShare.nftNumber || nftId.split("-")[1] || "preview"
            // URL slug should be lowercase, no spaces, no special characters, no dashes
            const urlSlug = collectionSlug.toLowerCase().replace(/[^a-z0-9]/g, "").replace(/-/g, "")
            const imageUrl = `https://nft.fragment.com/gift/${urlSlug}/${giftNumber}.webp`
            const animationUrl = `https://nft.fragment.com/gift/${urlSlug}/${giftNumber}.json`
            
            console.log(`[Webhook] Generated URLs: imageUrl=${imageUrl}, animationUrl=${animationUrl} (urlSlug=${urlSlug}, giftNumber=${giftNumber}, collectionSlug=${collectionSlug})`)
            
            // Add gift to user inventory (primary method)
            const result = await addUserGift(chatIdStr, {
              nftId,
              collectionName,
              collectionSlug,
              phone: userPhone || "unknown",
              telegramId: chatIdStr,
              quantity: 1,
              metadata: {
                giftName: displayName,
                rarity: "common",
                imageUrl,
                animationUrl,
              },
            })
            
            if (!result.success) {
              console.error(`[Webhook] Error adding gift to inventory: ${result.error}`)
              // Try alternative method using download-gift endpoint (like dad1)
              try {
                const downloadResponse = await fetch(`${WEBAPP_URL}/api/telegram/download-gift`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    telegramId: chatIdStr,
                    gift_link: giftShare.nftLink,
                  }),
                })
                const downloadResult = await downloadResponse.json()
                if (!downloadResult.success) {
                  await sendMessage(chatId, "❌ Ошибка при добавлении подарка в инвентарь.")
                  return NextResponse.json({ ok: true })
                }
                console.log(`[Webhook] Gift added via download-gift endpoint: ${downloadResult.message}`)
              } catch (downloadError) {
                console.error(`[Webhook] Error using download-gift endpoint: ${downloadError}`)
                await sendMessage(chatId, "❌ Ошибка при добавлении подарка в инвентарь.")
                return NextResponse.json({ ok: true })
              }
            } else {
              console.log(`[Webhook] Gift added successfully to inventory: ${nftId}`)
            }
            
            // Get creator info
            const creator = getUser(giftShare.creatorTelegramId)
            const creatorUsername = creator?.username || "пользователь"
            
            const successMessage = `🎁 *Подарок принят!*\n\n@${creatorUsername} передал вам [NFT подарок](${giftShare.nftLink}) через функцию обмена подарками Getgems прямо в чате Telegram.\n\nТеперь он в вашем инвентаре веб-приложения.`
            
            await sendMessage(chatId, successMessage, getWebAppKeyboard())
          } catch (error) {
            console.error("[Webhook] Error processing gift acceptance:", error)
            await sendMessage(chatId, "❌ Ошибка при обработке подарка.")
          }
          
          return NextResponse.json({ ok: true })
        }
        
        // Handle referral links
        const refMatch = text.match(/ref_(\d+)/)
        if (refMatch && !userData.referredBy) {
          const referrerId = refMatch[1]
          if (referrerId !== chatIdStr) {
            updateUser(chatIdStr, { referredBy: Number.parseInt(referrerId) })

            const referrer = getUser(referrerId)
            if (referrer) {
              const newCount = referrer.referralCount + 1
              let bonus = 0
              if (newCount === 5) bonus = 50
              else if (newCount === 15) bonus = 150
              else if (newCount === 30) bonus = 300
              else if (newCount === 50) bonus = 500

              updateUser(referrerId, {
                referralCount: newCount,
                balance: referrer.balance + bonus,
              })

              if (bonus > 0) {
                await sendMessage(
                  Number.parseInt(referrerId),
                  `🎉 *Новый реферал!*\n\n${firstName} присоединился по вашей ссылке.\n\n💰 Бонус: +${bonus} баллов`,
                )
              }
            }
          }
        }

        await sendMessage(
          chatId,
          `👋 Привет, *${firstName}*!\n\nДобро пожаловать в *MARKETPLACE* — твой NFT маркетплейс в Telegram!\n\n🎁 *Что тебя ждет:*\n• Покупай и продавай NFT подарки\n• Участвуй в сезонных событиях\n• Приглашай друзей и получай бонусы\n• Зарабатывай TON\n\nНажми кнопку ниже 👇`,
          getWebAppKeyboard(),
        )
      } else if (text === "/help") {
        await sendMessage(
          chatId,
          "📚 *Справка*\n\n/start - Запустить бота\n/market - Открыть маркет\n/profile - Профиль\n/referral - Реферальная программа\n/auth - Авторизация",
          getWebAppKeyboard(),
        )
      } else if (text === "/market") {
        await sendMessage(chatId, "🛍 Открой маркетплейс:", getWebAppKeyboard())
      } else if (text === "/profile") {
        const profile = getUser(chatIdStr)
        await sendMessage(
          chatId,
          `👤 *Твой профиль*\n\n💰 Баланс: *${profile?.balance || 0}* баллов\n🔥 Уровень: *${profile?.level || 1}*\n⭐ Рейтинг: *${profile?.rating || 0}*`,
          {
            inline_keyboard: [[{ text: "👤 Открыть профиль", web_app: { url: `${WEBAPP_URL}?tab=profile` } }]],
          },
        )
      } else if (text === "/referral") {
        const botInfo = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/getMe`).then((r) => r.json())
        const botUsername = botInfo.result?.username || "MarketplaceBot"
        const refLink = `https://t.me/${botUsername}?start=ref_${chatId}`
        const refCount = userData?.referralCount || 0

        await sendMessage(
          chatId,
          `👥 *Реферальная программа*\n\n🔗 *Твоя ссылка:*\n\`${refLink}\`\n\n📊 *Статистика:*\n• Приглашено: *${refCount}* друзей\n\n💰 *Награды:*\n• 5 друзей → +50 баллов\n• 15 друзей → +150 баллов\n• 30 друзей → +300 баллов\n• 50 друзей → +500 баллов`,
          {
            inline_keyboard: [
              [{ text: "📤 Поделиться", switch_inline_query: `Присоединяйся к MARKETPLACE! ${refLink}` }],
              [{ text: "👥 Партнеры", web_app: { url: `${WEBAPP_URL}?tab=partners` } }],
            ],
          },
        )
      } else if (text === "/auth") {
        await sendMessage(chatId, "🔐 *Авторизация*\n\nДля входа поделитесь номером телефона 👇", getContactKeyboard())
      } else {
        await sendMessage(chatId, "👋 Используй кнопку ниже:", getWebAppKeyboard())
      }
    }

    // Handle inline queries
    if (update.inline_query) {
      const inlineQuery = update.inline_query
      const queryText = inlineQuery.query?.trim() || ""
      const fromUser = inlineQuery.from
      const fromUserId = fromUser.id.toString()
      
      // Get bot username for share link
      const botInfo = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/getMe`).then((r) => r.json())
      const botUsername = botInfo.result?.username || "MarketplaceBot"
      
      let results: any[] = []
      
      if (!queryText) {
        // Show instruction if no query
        results = [
          {
            type: "article",
            id: "instruction",
            title: "Как создать подарочную ссылку",
            description: "Введите ссылку на NFT после @usernamebot",
            input_message_content: {
              message_text: "Для создания подарочной ссылки введите: @usernamebot {ссылка на NFT}",
            },
          },
        ]
      } else {
        // Parse NFT link
        const nftInfo = parseNFTLink(queryText)
        
        if (!nftInfo) {
          // Invalid link
          results = [
            {
              type: "article",
              id: "invalid_link",
              title: "Неверная ссылка на NFT",
              description: "Пожалуйста, введите корректную ссылку на NFT",
              input_message_content: {
                message_text: "❌ Неверная ссылка на NFT. Используйте формат: http://t.me/nft/название-номер",
              },
            },
          ]
        } else {
          // Create gift share
          const giftShare = createGiftShare(
            queryText,
            nftInfo.name,
            nftInfo.number,
            fromUserId,
          )
          
          const messageText = `🎁 Вам дарят NFT: [${nftInfo.displayName}](${queryText})\n\nДля принятия нажмите кнопку ниже.`
          
          results = [
            {
              type: "article",
              id: `gift_${giftShare.shareToken}`,
              title: `🎁 Подарить ${nftInfo.displayName}`,
              description: `NFT: ${nftInfo.displayName}`,
              input_message_content: {
                message_text: messageText,
                parse_mode: "Markdown",
              },
              reply_markup: {
                inline_keyboard: [
                  [
                    { text: "📱 Посмотреть", url: queryText },
                  ],
                  [
                    {
                      text: "🎁 Принять подарок",
                      url: `https://t.me/${botUsername}?start=gift_${giftShare.shareToken}`,
                    },
                  ],
                ],
              },
            },
          ]
        }
      }
      
      // Answer inline query
      await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/answerInlineQuery`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inline_query_id: inlineQuery.id,
          results: results,
          cache_time: 1,
        }),
      })
      
      return NextResponse.json({ ok: true })
    }

    if (update.callback_query) {
      const callback = update.callback_query
      const chatId = callback.message?.chat?.id
      const data = callback.data

      // Отвечаем на callback чтобы убрать loading
      await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/answerCallbackQuery`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ callback_query_id: callback.id }),
      })

      if (data === "auth" && chatId) {
        await sendMessage(chatId, "🔐 *Авторизация*\n\nДля входа поделитесь номером телефона 👇", getContactKeyboard())
      }
    }

    return NextResponse.json({ ok: true })
  } catch (error) {
    console.error("Webhook error:", error)
    return NextResponse.json({ ok: true })
  }
}
