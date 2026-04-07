import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

export const getSessions = () => api.get('/sessions').then(r => r.data)
export const getAvailability = (date) => api.get('/availability', { params: { date } }).then(r => r.data)
export const createBooking = (data) => api.post('/bookings', data).then(r => r.data)
export const createCheckoutSession = (data) => api.post('/create-checkout-session', data).then(r => r.data)
export const getBookingByStripeSession = (stripeSessionId) =>
  api.get(`/booking-by-session/${stripeSessionId}`).then(r => r.data)
