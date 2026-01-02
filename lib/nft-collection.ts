export async function getNFTInfo(id: string) {
  return { id, name: `NFT ${id}`, image: null }
}

export function getRarityBgColor(rarity?: string) {
  return '#ffffff'
}

export default { getNFTInfo, getRarityBgColor }
