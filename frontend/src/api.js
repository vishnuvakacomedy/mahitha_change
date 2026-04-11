import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

// ── Public ──────────────────────────────────────────────────────────────────
export const getSessions = () => api.get('/sessions').then(r => r.data)
export const getAvailability = (date) =>
  api.get('/availability', { params: { date } }).then(r => r.data)
export const createCheckoutSession = (data) =>
  api.post('/create-checkout-session', data).then(r => r.data)
export const getBookingByStripeSession = (stripeSessionId) =>
  api.get(`/booking-by-session/${stripeSessionId}`).then(r => r.data)

// ── Admin (Basic Auth) ──────────────────────────────────────────────────────
const withAuth = (username, password) => ({ auth: { username, password } })

export const adminGetBookings = (u, p) =>
  api.get('/admin/bookings', withAuth(u, p)).then(r => r.data)
export const adminGetSlots = (u, p) =>
  api.get('/admin/slots', withAuth(u, p)).then(r => r.data)
export const adminAddSlot = (slot, u, p) =>
  api.post('/admin/slots', slot, withAuth(u, p)).then(r => r.data)
export const adminDeleteSlot = (id, u, p) =>
  api.delete(`/admin/slots/${id}`, withAuth(u, p)).then(r => r.data)
export const adminCancelBooking = (id, u, p) =>
  api.delete(`/admin/bookings/${id}`, withAuth(u, p)).then(r => r.data)

// ── Eastern Time formatting helpers ─────────────────────────────────────────
// We store slot times as UTC ISO strings but always *display* them in ET.
// Using Intl avoids pulling in a timezone library.
const ET = 'America/New_York'

/** Calendar-day key like "2026-04-15" for an ISO string, evaluated in ET. */
export function etDateKey(iso) {
  // en-CA gives YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: ET,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(iso))
}

/** Calendar-day key for a local Date object, ignoring its time/zone (e.g. from react-calendar). */
export function localDateKey(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** "7:00 PM" in ET. */
export function etTime(iso) {
  return new Intl.DateTimeFormat('en-US', {
    timeZone: ET,
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(new Date(iso))
}

/** "Wednesday, April 15" (local weekday/month/day – used for the calendar header label). */
export function weekdayMonthDay(date) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  }).format(date)
}

/** "Wednesday, April 15, 2026 · 7:00 PM EDT" — used for confirmation banners. */
export function etLongDateTime(iso) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: ET,
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZoneName: 'short',
  }).formatToParts(new Date(iso))

  const get = (type) => parts.find(p => p.type === type)?.value || ''
  const weekday = get('weekday')
  const month = get('month')
  const day = get('day')
  const year = get('year')
  const hour = get('hour')
  const minute = get('minute')
  const dayPeriod = get('dayPeriod')
  const tz = get('timeZoneName')
  return `${weekday}, ${month} ${day}, ${year} · ${hour}:${minute} ${dayPeriod} ${tz}`
}
