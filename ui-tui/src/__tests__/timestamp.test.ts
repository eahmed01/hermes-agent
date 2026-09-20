import { describe, expect, it } from 'vitest'

import { formatMessageTimestamp } from '../lib/timestamp.js'

const TS = new Date(2026, 8, 17, 14, 5, 9).getTime() / 1000  // local 2026-09-17 14:05:09

describe('formatMessageTimestamp', () => {
  it('formats the default %H:%M', () => {
    expect(formatMessageTimestamp(TS, '%H:%M')).toBe('14:05')
  })

  it('supports the common directives', () => {
    expect(formatMessageTimestamp(TS, '%H:%M:%S')).toBe('14:05:09')
    expect(formatMessageTimestamp(TS, '%Y-%m-%d %H:%M')).toBe('2026-09-17 14:05')
    expect(formatMessageTimestamp(TS, '%a %b %d %H:%M')).toBe('Thu Sep 17 14:05')
    expect(formatMessageTimestamp(TS, '%I:%M %p')).toBe('02:05 PM')
  })

  it('renders unknown directives verbatim', () => {
    expect(formatMessageTimestamp(TS, '%Q %H')).toBe('%Q 14')
  })
})
