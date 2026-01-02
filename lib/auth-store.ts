export const authStore = {
  pendingCodes: new Map<string, any>(),
  giftRegistry: new Set<string>(),
}

export async function getTelegramAuth() { return null }
export async function updateTelegramAuth() { return null }
export async function createSession() { return {} }
export async function getSession() { return null }
export async function getSessionByTelegramId() { return null }
export async function setVerificationCode() { return null }
export async function generateCode() { return Math.floor(10000 + Math.random() * 90000).toString() }
export async function getVerificationCode() { return null }
export async function deleteVerificationCode() { return null }
export async function setTelegramAuth() { return null }

export async function addUserGift() { return null }
export async function getUserPhone() { return null }
export async function getAuthRequestByTelegramId() { return null }
export async function createAuthRequest() { return null }
export async function getLatestAuthRequestByPhone() { return null }
export async function getAuthRequestById() { return null }
export async function updateAuthRequest() { return null }
export async function linkUserPhone() { return null }
export async function getPendingAuthRequests() { return [] }

export async function getUserGifts() { return [] }
export async function getUserGiftsByPhone() { return [] }
export async function getTotalGiftsCount() { return 0 }
export async function removeUserGift() { return null }

export async function getUser() { return null }
export async function setUser() { return null }
export async function updateUser() { return null }

export async function createGiftShare() { return null }
export async function getGiftShareByToken() { return null }
export async function acceptGiftShare() { return null }

export async function getAllUserPhones() { return [] }

export default authStore
