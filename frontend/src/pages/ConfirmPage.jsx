import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { format, parseISO } from 'date-fns'
import { getBookingByStripeSession } from '../api'
import styles from './ConfirmPage.module.css'

export default function ConfirmPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const stripeSessionId = searchParams.get('session_id')

  const [booking, setBooking] = useState(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!stripeSessionId) { setLoading(false); return }
    let attempts = 0
    const poll = setInterval(async () => {
      try {
        const data = await getBookingByStripeSession(stripeSessionId)
        setBooking(data)
        clearInterval(poll)
        setLoading(false)
      } catch {
        if (++attempts >= 8) {
          clearInterval(poll)
          setLoading(false)
          setFailed(true)
        }
      }
    }, 2000)
    return () => clearInterval(poll)
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
              <strong>{format(parseISO(booking.slot_datetime), 'EEEE, MMMM d, yyyy · h:mm a')}</strong>
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

        {failed && (
          <p className={styles.notice}>
            Your payment was received. If you don't receive a confirmation email within a few minutes, contact mahitha@mahithavaka.com.
          </p>
        )}

        <button className={styles.homeBtn} onClick={() => navigate('/')}>
          Back to Home
        </button>
      </div>
    </div>
  )
}
