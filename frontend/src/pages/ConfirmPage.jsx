import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getBookingByStripeSession, etLongDateTime } from '../api'
import styles from './ConfirmPage.module.css'

// Poll for ~45 seconds total: Stripe webhooks can take a while under load.
const POLL_INTERVAL_MS = 2000
const MAX_ATTEMPTS = 22

export default function ConfirmPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const stripeSessionId = searchParams.get('session_id')

  const [booking, setBooking] = useState(null)
  const [loading, setLoading] = useState(true)
  const [stillWaiting, setStillWaiting] = useState(false)

  useEffect(() => {
    if (!stripeSessionId) {
      setLoading(false)
      return
    }
    let attempts = 0
    let cancelled = false

    const poll = setInterval(async () => {
      if (cancelled) return
      try {
        const data = await getBookingByStripeSession(stripeSessionId)
        if (cancelled) return
        setBooking(data)
        setLoading(false)
        clearInterval(poll)
      } catch {
        if (++attempts >= MAX_ATTEMPTS) {
          clearInterval(poll)
          if (!cancelled) {
            setLoading(false)
            setStillWaiting(true)
          }
        }
      }
    }, POLL_INTERVAL_MS)

    return () => { cancelled = true; clearInterval(poll) }
  }, [stripeSessionId])

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.card}>
          <div className={styles.spinner} />
          <p className={styles.sub}>Confirming your booking…</p>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.checkmark}>✓</div>
        <h1>You're Booked!</h1>
        <p className={styles.sub}>
          Payment received. Mahitha will send you a Zoom link shortly.
        </p>

        {booking && (
          <div className={styles.details}>
            <div className={styles.row}>
              <span>Session</span>
              <strong>Clarity Coaching Session</strong>
            </div>
            <div className={styles.row}>
              <span>Date &amp; Time</span>
              <strong>{etLongDateTime(booking.slot_datetime)}</strong>
            </div>
            <div className={styles.row}>
              <span>Name</span>
              <strong>{booking.name}</strong>
            </div>
            <div className={styles.row}>
              <span>Email</span>
              <strong>{booking.email}</strong>
            </div>
            <div className={styles.row}>
              <span>Amount Paid</span>
              <strong>$80.00</strong>
            </div>
          </div>
        )}

        {stillWaiting && (
          <p className={styles.notice}>
            We received your payment. Your confirmation email will arrive shortly — if you don't
            see it within a few minutes, contact mahitha@mahithavaka.com.
          </p>
        )}

        <button className={styles.homeBtn} onClick={() => navigate('/')}>
          Back to Home
        </button>
      </div>
    </div>
  )
}
