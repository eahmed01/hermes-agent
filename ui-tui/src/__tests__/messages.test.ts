import { PassThrough } from 'stream'

import { renderSync } from '@hermes/ink'
import React from 'react'
import { describe, expect, it } from 'vitest'

import { MessageLine } from '../components/messageLine.js'
import { toTranscriptMessages } from '../domain/messages.js'
import { upsert } from '../lib/messages.js'
import { stripAnsi } from '../lib/text.js'
import { formatMessageTimestamp } from '../lib/timestamp.js'
import { DEFAULT_THEME } from '../theme.js'

describe('toTranscriptMessages', () => {
  it('preserves assistant tool-call rows so resume does not drop prior turns', () => {
    const rows = [
      { role: 'user', text: 'first prompt', timestamp: 1758123456 },
      { role: 'tool', context: 'repo', name: 'search_files', text: 'ignored raw result' },
      { role: 'assistant', text: 'first answer', timestamp: 1758123456 },
      { role: 'user', text: 'second prompt' }
    ]

    expect(toTranscriptMessages(rows).map(msg => [msg.role, msg.text])).toEqual([
      ['user', 'first prompt'],
      ['assistant', 'first answer'],
      ['user', 'second prompt']
    ])
    expect(toTranscriptMessages(rows)[1]?.tools?.[0]).toContain('Search Files')
    // Row timestamps survive onto user/assistant Msgs; tool rows (merged into
    // the trail) and rows without a stored timestamp keep no stamp.
    expect(toTranscriptMessages(rows)[0]?.timestamp).toBe(1758123456)
    expect(toTranscriptMessages(rows)[1]?.timestamp).toBe(1758123456)
    expect(toTranscriptMessages(rows)[2]?.timestamp).toBeUndefined()
  })
})

describe('MessageLine', () => {
  it('preserves a separator after compound user prompt glyphs in transcript rows', () => {
    const stdout = new PassThrough()
    const stdin = new PassThrough()
    const stderr = new PassThrough()
    let output = ''

    Object.assign(stdout, { columns: 80, isTTY: false, rows: 24 })
    Object.assign(stdin, { isTTY: false })
    Object.assign(stderr, { isTTY: false })
    stdout.on('data', chunk => {
      output += chunk.toString()
    })

    const t = {
      ...DEFAULT_THEME,
      brand: { ...DEFAULT_THEME.brand, prompt: 'Ψ >' }
    }

    const instance = renderSync(
      React.createElement(MessageLine, {
        cols: 80,
        msg: { role: 'user', text: 'Okay' },
        t
      }),
      {
        patchConsole: false,
        stderr: stderr as NodeJS.WriteStream,
        stdin: stdin as NodeJS.ReadStream,
        stdout: stdout as NodeJS.WriteStream
      }
    )

    instance.unmount()
    instance.cleanup()

    const renderedLine = stripAnsi(output)
      .split('\n')
      .find(line => line.includes('Okay'))

    expect(renderedLine).toContain('Ψ > Okay')
  })

  it('renders the timestamp footer below the message only when showTimestamps is on', () => {
    const ts = 1758123456
    const stamp = formatMessageTimestamp(ts, '%H:%M')

    const renderLines = (extra: Record<string, unknown>): string[] => {
      const stdout = new PassThrough()
      const stdin = new PassThrough()
      const stderr = new PassThrough()
      let output = ''

      Object.assign(stdout, { columns: 80, isTTY: false, rows: 24 })
      Object.assign(stdin, { isTTY: false })
      Object.assign(stderr, { isTTY: false })
      stdout.on('data', chunk => {
        output += chunk.toString()
      })

      const t = {
        ...DEFAULT_THEME,
        brand: { ...DEFAULT_THEME.brand, prompt: 'Ψ >' }
      }

      const instance = renderSync(
        React.createElement(MessageLine, { cols: 80, t, ...extra }),
        {
          patchConsole: false,
          stderr: stderr as NodeJS.WriteStream,
          stdin: stdin as NodeJS.ReadStream,
          stdout: stdout as NodeJS.WriteStream
        }
      )

      instance.unmount()
      instance.cleanup()

      return stripAnsi(output).split('\n')
    }

    // Fixture text has no time-like substring, so the only occurrence of the
    // stamp string is the footer line.
    const lines = renderLines({ msg: { role: 'user', text: 'hello', timestamp: ts }, showTimestamps: true })
    const msgIdx = lines.findIndex(line => line.includes('hello'))
    const stampIdx = lines.findIndex(line => line.includes(stamp))

    expect(msgIdx).toBeGreaterThanOrEqual(0)
    expect(stampIdx).toBeGreaterThan(msgIdx)

    const hidden = renderLines({ msg: { role: 'user', text: 'hello', timestamp: ts } })
    expect(hidden.findIndex(line => line.includes(stamp))).toBe(-1)
  })
})

describe('upsert', () => {
  it('appends when last role differs', () => {
    expect(upsert([{ role: 'user', text: 'hi' }], 'assistant', 'hello')).toHaveLength(2)
  })

  it('replaces when last role matches', () => {
    expect(upsert([{ role: 'assistant', text: 'partial' }], 'assistant', 'full')[0]!.text).toBe('full')
  })

  it('appends to empty', () => {
    expect(upsert([], 'user', 'first')).toEqual([{ role: 'user', text: 'first' }])
  })

  it('does not mutate', () => {
    const prev = [{ role: 'user' as const, text: 'hi' }]
    upsert(prev, 'assistant', 'yo')
    expect(prev).toHaveLength(1)
  })
})
