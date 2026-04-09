import { useEffect, useState } from 'react'
import { format, parseISO } from 'date-fns'
import axios from 'axios'
import styles from './AdminPage.module.css'

const api = axios.create({ baseURL: '' })

function withAuth(username, password) {
  return { auth: { username, password } }
}

export default function AdminPage() {
  const [creds, setCreds] = useState({ username: '', password: '' })
  const [authed, setAuthed] = useState(false)
  const [authError, setAuthError] = useState('')
  const [bookings, setBookings] = useState([])
  const [slots, setSlots] = useState([])
  const [tab, setTab] = useState('bookings')
  const [newSlot, setNewSlot] = useState({ date: '', hour: 17 })
  const [message, setMessage] = useState('')

  async function login(e) {
    e.preventDefault()
    try {
      await api.get('/admin/bookings', withAuth(creds.username, creds.password))
      setAuthed(true)
      setAuthError('')
      loadData(creds.username, creds.password)
    } catch {
      setAuthError('Invalid username or password')
    }
  }

  async function loadData(u, p) {
    const [b, s] = await Promise.all([
      api.get('/admin/bookings', withAuth(u || creds.username, p || creds.password)).then(r => r.data),
      api.get('/admin/slots', withAuth(u || creds.username, p || creds.password)).then(r => r.data),
    ])
    setBookings(b)
    setSlots(s)
  }

  async function addSlot(e) {
    e.preventDefault()
    try {
      await api.post('/admin/slots', newSlot, withAuth(creds.username, creds.password))
      setMessage('Slot added!')
      loadData()
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Error adding slot')
    }
    setTimeout(() => setMessage(''), 3000)
  }

  async function deleteSlot(id) {
    if (!confirm('Remove this slot?')) return
    try {
      await api.delete(`/admin/slots/${id}`, withAuth(creds.username, creds.password))
      setMessage('Slot removed')
      loadData()
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Error removing slot')
    }
    setTimeout(() => setMessage(''), 3000)
  }

  async function cancelBooking(id) {
    if (!confirm('Cancel this booking? The slot will be freed up.')) return
    try {
      await api.delete(`/admin/bookings/${id}`, withAuth(creds.username, creds.password))
      setMessage('Booking cancelled')
      loadData()
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Error cancelling booking')
    }
    setTimeout(() => setMessage(''), 3000)
  }

  const upcomingBookings = bookings
    .filter(b => b.status !== 'cancelled' && new Date(b.slot_datetime) > new Date())
    .sort((a, b) => new Date(a.slot_datetime) - new Date(b.slot_datetime))

  const availableSlots = slots
    .filter(s => !s.booked && new Date(s.datetime) > new Date())
    .sort((a, b) => new Date(a.datetime) - new Date(b.datetime))

  if (!authed) {
    return (
      <div className={styles.loginPage}>
        <form className={styles.loginCard} onSubmit={login}>
          <h1>Admin Login</h1>
          <label>Username
            <input value={creds.username} onChange={e => setCreds(c => ({ ...c, username: e.target.value }))} />
          </label>
          <label>Password
            <input type="password" value={creds.password} onChange={e => setCreds(c => ({ ...c, password: e.target.value }))} />
          </label>
          {authError && <p className={styles.error}>{authError}</p>}
          <button type="submit" className={styles.btn}>Sign In</button>
        </form>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Mahitha Vaka — Admin</h1>
        <button className={styles.btnOutline} onClick={() => setAuthed(false)}>Sign Out</button>
      </header>

      {message && <div className={styles.toast}>{message}</div>}

      <div className={styles.tabs}>
        <button className={`${styles.tab} ${tab === 'bookings' ? styles.activeTab : ''}`} onClick={() => setTab('bookings')}>
          Bookings ({upcomingBookings.length})
        </button>
        <button className={`${styles.tab} ${tab === 'slots' ? styles.activeTab : ''}`} onClick={() => setTab('slots')}>
          Manage Slots ({availableSlots.length} open)
        </button>
      </div>

      {/* ── Bookings tab ── */}
      {tab === 'bookings' && (
        <div className={styles.section}>
          {upcomingBookings.length === 0 ? (
            <p className={styles.empty}>No upcoming bookings.</p>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Date & Time (EST)</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Goals</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {upcomingBookings.map(b => (
                  <tr key={b.id}>
                    <td>{format(parseISO(b.slot_datetime), 'MMM d, yyyy · h:mm a')}</td>
                    <td>{b.name}</td>
                    <td><a href={`mailto:${b.email}`}>{b.email}</a></td>
                    <td>{b.phone || '—'}</td>
                    <td className={styles.goalCell}>{b.goal}</td>
                    <td>
                      <button className={styles.btnDanger} onClick={() => cancelBooking(b.id)}>Cancel</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ── Slots tab ── */}
      {tab === 'slots' && (
        <div className={styles.section}>
          <form className={styles.addSlotForm} onSubmit={addSlot}>
            <h2>Add a Slot</h2>
            <div className={styles.addSlotRow}>
              <label>Date
                <input type="date" value={newSlot.date}
                  onChange={e => setNewSlot(s => ({ ...s, date: e.target.value }))} required />
              </label>
              <label>Hour (EST)
                <select value={newSlot.hour} onChange={e => setNewSlot(s => ({ ...s, hour: Number(e.target.value) }))}>
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>
                      {i === 0 ? '12:00 AM' : i < 12 ? `${i}:00 AM` : i === 12 ? '12:00 PM' : `${i - 12}:00 PM`}
                    </option>
                  ))}
                </select>
              </label>
              <button type="submit" className={styles.btn}>Add Slot</button>
            </div>
          </form>

          <h2 style={{ marginBottom: '1rem' }}>Open Slots</h2>
          {availableSlots.length === 0 ? (
            <p className={styles.empty}>No open slots available.</p>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr><th>Date & Time (EST)</th><th></th></tr>
              </thead>
              <tbody>
                {availableSlots.map(s => (
                  <tr key={s.id}>
                    <td>{format(parseISO(s.datetime), 'EEEE, MMM d, yyyy · h:mm a')}</td>
                    <td>
                      <button className={styles.btnDanger} onClick={() => deleteSlot(s.id)}>Remove</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
