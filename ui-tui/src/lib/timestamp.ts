// Minimal strftime-subset for display.timestamp_format (TUI parity with
// the classic CLI's Python strftime). Supported directives: %H %I %M %S %p %y %Y
// %m %d %b %a %% — anything else renders verbatim. Local time, matching the
// CLI's datetime.now().strftime (cli.py:5486, 5787). %a/%b/%p are
// hardcoded English here; Python strftime localizes them under a
// non-English LC_TIME — a conscious divergence (directive surface matches,
// not locale).
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const pad2 = (n: number) => String(n).padStart(2, '0')

export const formatMessageTimestamp = (tsSec: number, format: string): string => {
  const d = new Date(tsSec * 1000)
  let out = ''

  for (let i = 0; i < format.length; i += 1) {
    const c = format[i]!

    if (c !== '%') {
      out += c

      continue
    }

    const token = format[i + 1]
    i += 1

    switch (token) {
      case 'H':
        out += pad2(d.getHours())

        break

      case 'I':
        out += pad2(((d.getHours() + 11) % 12) + 1)

        break

      case 'M':
        out += pad2(d.getMinutes())

        break

      case 'S':
        out += pad2(d.getSeconds())

        break

      case 'p':
        out += d.getHours() >= 12 ? 'PM' : 'AM'

        break

      case 'y':
        out += pad2(d.getFullYear() % 100)

        break

      case 'Y':
        out += String(d.getFullYear())

        break

      case 'm':
        out += pad2(d.getMonth() + 1)

        break

      case 'd':
        out += pad2(d.getDate())

        break

      case 'b':
        out += MONTHS[d.getMonth()]!

        break

      case 'a':
        out += DAYS[d.getDay()]!

        break

      case '%':
        out += '%'

        break

      default:
        out += `%${token ?? ''}`
    }
  }

  return out
}
