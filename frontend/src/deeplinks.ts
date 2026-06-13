import type { ActionCard, Platform } from './types'

// Swimlane order + display labels. Mirrors backend cards.PLATFORMS.
export const PLATFORMS: { id: Platform; label: string }[] = [
  { id: 'reddit', label: 'Reddit' },
  { id: 'hackernews', label: 'Hacker News' },
  { id: 'x', label: 'X' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'indiehackers', label: 'Indie Hackers' },
  { id: 'other', label: 'Other' },
]

// Classify a draft to a swimlane — used when deriving cards from the live run in the
// browser (the server does the same at seed time). Order matters: 'indie' before 'hacker'.
export function classifyPlatform(...hints: (string | undefined | null)[]): Platform {
  const blob = hints.filter(Boolean).join(' ').toLowerCase()
  if (blob.includes('reddit')) return 'reddit'
  if (blob.includes('indie')) return 'indiehackers'
  if (blob.includes('hacker') || blob.includes('ycombinator') || blob.includes('news.yc')) return 'hackernews'
  if (blob.includes('linkedin')) return 'linkedin'
  if (blob.includes('twitter') || blob.includes('x.com')) return 'x'
  return 'other'
}

function tweetId(url?: string | null): string | null {
  const m = (url || '').match(/status\/(\d+)/)
  return m ? m[1] : null
}

export type CardAction = {
  // the button label + url for the "open/post" action; prefills===true means the body
  // rides in the URL (true 1-click post); false means open-only and the user pastes.
  openLabel: string
  openUrl: string | null
  prefills: boolean
}

/**
 * The deep-link recipe for a card. There is NO uniform "1-click post":
 *  - kind=post: real prefill where the platform supports it (X tweet, Reddit self-post).
 *  - kind=reply: no platform offers reply-body prefill — open the thread, paste the copy.
 *    (X is the one exception: intent/tweet?in_reply_to= prefills a reply.)
 */
export function cardAction(card: ActionCard): CardAction {
  const text = encodeURIComponent(card.body || '')
  const p = card.platform
  const isPost = card.kind === 'post'

  if (p === 'x') {
    const tid = tweetId(card.target_url)
    if (isPost) return { openLabel: 'Post on X', openUrl: `https://twitter.com/intent/tweet?text=${text}`, prefills: true }
    if (tid) return { openLabel: 'Reply on X', openUrl: `https://twitter.com/intent/tweet?in_reply_to=${tid}&text=${text}`, prefills: true }
    return { openLabel: 'Open thread', openUrl: card.target_url || 'https://twitter.com', prefills: false }
  }

  if (p === 'reddit') {
    if (isPost) {
      const sub = card.metadata?.subreddit
      if (sub) {
        const title = encodeURIComponent(card.title || '')
        return { openLabel: 'Post to Reddit', openUrl: `https://www.reddit.com/r/${sub}/submit?title=${title}&text=${text}`, prefills: true }
      }
      return { openLabel: 'Open Reddit', openUrl: 'https://www.reddit.com/submit', prefills: false }
    }
    return { openLabel: 'Open thread', openUrl: card.target_url || null, prefills: false }
  }

  if (p === 'hackernews') {
    return isPost
      ? { openLabel: 'Open HN', openUrl: 'https://news.ycombinator.com/submit', prefills: false }
      : { openLabel: 'Open thread', openUrl: card.target_url || null, prefills: false }
  }

  if (p === 'linkedin') {
    return { openLabel: isPost ? 'Open LinkedIn' : 'Open thread', openUrl: card.target_url || 'https://www.linkedin.com/feed/?shareActive=true', prefills: false }
  }

  // indiehackers + other: open the thread/source if we have one, else copy-only.
  return { openLabel: 'Open thread', openUrl: card.target_url || null, prefills: false }
}
