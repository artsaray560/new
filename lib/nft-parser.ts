export function parseNFTLink(link: string) {
  return { id: String(link || ""), source: link }
}

export default parseNFTLink
