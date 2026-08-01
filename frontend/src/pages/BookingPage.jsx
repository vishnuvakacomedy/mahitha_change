import { useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router'
import Calendar from 'react-calendar'
import 'react-calendar/dist/Calendar.css'
import {
  getSessions,
  getAvailability,
  createCheckoutSession,
  etDateKey,
  localDateKey,
  etTime,
  weekdayMonthDay,
  etLongDateTime,
} from '../api'
import styles from './BookingPage.module.css'

const GOAL_OPTIONS = [
  'Career clarity', 'Life decisions', 'Overthinking', 'Relationships',
  'Self-confidence', 'Work-life balance', 'Purpose & direction', 'Other',
]

export default function BookingPage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const wasCancelled = searchParams.get('cancelled') === 'true'

  const [session, setSession] = useState(null)
  const [slots, setSlots] = useState([])
  const [selectedDate, setSelectedDate] = useState(null)
  const [selectedSlot, setSelectedSlot] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    name: '', email: '', phone: '',
    emotional_state: '',
    life_impact: '',
    goals: [],
    commitment: 5,
  })

  function handleGoalToggle(goal) {
    setForm(f => ({
      ...f,
      goals: f.goals.includes(goal)
        ? f.goals.filter(g => g !== goal)
        : [...f.goals, goal]
    }))
  }

  useEffect(() => {
    let cancelled = false
    setLoadError('')
    Promise.all([getSessions(), getAvailability()])
      .then(([list, availability]) => {
        if (cancelled) return
        setSession(list.find(s => s.id === sessionId) || null)
        setSlots(availability)
      })
      .catch(() => {
        if (!cancelled) setLoadError("We couldn't load availability. Please refresh and try again.")
      })
    return () => { cancelled = true }
  }, [sessionId])

  // Pre-compute the set of ET calendar-day keys that have available slots,
  // so tile lookup is O(1) and uses Eastern Time (not the viewer's local tz).
  const availableDays = new Set(slots.map(s => etDateKey(s.datetime)))
  const selectedKey = selectedDate ? localDateKey(selectedDate) : null
  const slotsForDate = selectedKey
    ? slots.filter(s => etDateKey(s.datetime) === selectedKey)
    : []

  function tileDisabled({ date, view }) {
    if (view !== 'month') return false
    return !availableDays.has(localDateKey(date))
  }

  function handleFormChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (form.goals.length === 0) {
      setError('Please choose at least one area you want clarity on.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const result = await createCheckoutSession({
        slot_id: selectedSlot.id,
        session_id: sessionId,
        name: form.name,
        email: form.email,
        phone: form.phone,
        emotional_state: form.emotional_state,
        life_impact: form.life_impact,
        goals: form.goals,
        commitment: form.commitment,
      })
      window.location.href = result.checkout_url
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const timezone = 'Eastern Time (ET)'

  return (
    <div className={styles.page}>
      <button className={styles.back} onClick={() => navigate('/')}>← Back</button>

      <div className={styles.layout}>

        {/* ── Left Panel ── */}
        <aside className={styles.sidebar}>
          <img src="/imgs/mahitha.avif" alt="Mahitha Vaka" className={styles.avatar} />
          <p className={styles.coachName}>Mahitha Vaka</p>

          {session && (
            <>
              <h1 className={styles.sessionTitle}>{session.title}</h1>
              <p className={styles.sessionDesc}>{session.description}</p>

              <div className={styles.metaList}>
                <div className={styles.metaItem}>
                  <span className={styles.metaIcon}>⏱</span>
                  <span>{session.duration_minutes} minutes</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaIcon}>💻</span>
                  <span>{session.meeting_type}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaIcon}>💰</span>
                  <span>${session.price}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaIcon}>🌐</span>
                  <span>{timezone}</span>
                </div>
              </div>
            </>
          )}
        </aside>

        {/* ── Right Panel ── */}
        <main className={styles.main}>

          {loadError && <p className={styles.error}>{loadError}</p>}
          {wasCancelled && !loadError && (
            <p className={styles.error}>
              Checkout was cancelled — your card was not charged. Pick a time below to try again.
            </p>
          )}

          {!showForm ? (
            <>
              <h2 className={styles.panelTitle}>Select a Date &amp; Time</h2>

              <Calendar
                onChange={date => { setSelectedDate(date); setSelectedSlot(null) }}
                value={selectedDate}
                tileDisabled={tileDisabled}
                minDate={new Date()}
                next2Label={null}
                prev2Label={null}
              />

              {selectedDate && (
                <div className={styles.slotsSection}>
                  <h3 className={styles.slotsTitle}>
                    {weekdayMonthDay(selectedDate)}
                  </h3>
                  <p className={styles.tzNote}>All times in Eastern Time</p>
                  {slotsForDate.length === 0 ? (
                    <p className={styles.noSlots}>No available times on this day.</p>
                  ) : (
                    <div className={styles.slots}>
                      {slotsForDate.map(slot => (
                        <button
                          key={slot.id}
                          className={`${styles.slotBtn} ${selectedSlot?.id === slot.id ? styles.slotSelected : ''}`}
                          onClick={() => setSelectedSlot(slot)}
                        >
                          {etTime(slot.datetime)}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {selectedSlot && (
                <button className={styles.continueBtn} onClick={() => setShowForm(true)}>
                  Continue →
                </button>
              )}
            </>
          ) : (
            <>
              <button className={styles.backLink} onClick={() => setShowForm(false)}>
                ← Change time
              </button>

              <div className={styles.selectedSlotBanner}>
                <span className={styles.metaIcon}>📅</span>
                <strong>{etLongDateTime(selectedSlot.datetime)}</strong>
              </div>

              <h2 className={styles.panelTitle}>Your Details</h2>

              <form className={styles.form} onSubmit={handleSubmit}>
                <label>Full Name *
                  <input name="name" required value={form.name} onChange={handleFormChange} placeholder="Jane Smith" />
                </label>
                <label>Email *
                  <input name="email" type="email" required value={form.email} onChange={handleFormChange} placeholder="jane@example.com" />
                </label>
                <label>Phone
                  <input name="phone" value={form.phone} onChange={handleFormChange} placeholder="+1 (555) 000-0000" />
                </label>
                <label>What's your current emotional state or internal block? *
                  <textarea name="emotional_state" required rows={4} value={form.emotional_state} onChange={handleFormChange}
                    placeholder="Describe what's been weighing on you mentally or emotionally…" />
                </label>
                <label>How is this affecting your day-to-day life? *
                  <textarea name="life_impact" required rows={4} value={form.life_impact} onChange={handleFormChange}
                    placeholder="Share how this is showing up in your work, relationships, or decisions…" />
                </label>

                <div className={styles.checkboxGroup}>
                  <span className={styles.checkboxLabel}>What areas would you like clarity on? *</span>
                  <div className={styles.checkboxGrid}>
                    {GOAL_OPTIONS.map(goal => (
                      <label key={goal} className={styles.checkboxItem}>
                        <input
                          type="checkbox"
                          checked={form.goals.includes(goal)}
                          onChange={() => handleGoalToggle(goal)}
                        />
                        {goal}
                      </label>
                    ))}
                  </div>
                </div>

                <div className={styles.scaleGroup}>
                  <span className={styles.checkboxLabel}>
                    How committed are you to creating change? *&nbsp;
                    <strong style={{ color: 'var(--primary)' }}>{form.commitment}/10</strong>
                  </span>
                  <input
                    type="range" min="1" max="10"
                    value={form.commitment}
                    onChange={e => setForm(f => ({ ...f, commitment: Number(e.target.value) }))}
                    className={styles.slider}
                  />
                  <div className={styles.scaleLabels}>
                    <span>Just exploring</span>
                    <span>Fully committed</span>
                  </div>
                </div>

                {error && <p className={styles.error}>{error}</p>}

                <button type="submit" className={styles.continueBtn} disabled={loading}>
                  {loading ? 'Booking…' : 'Confirm Booking'}
                </button>
              </form>
            </>
          )}
        </main>
      </div>
    </div>
  )
}
