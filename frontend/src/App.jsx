import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import BookingPage from './pages/BookingPage'
import ConfirmPage from './pages/ConfirmPage'
import './index.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/book/:sessionId" element={<BookingPage />} />
        <Route path="/confirm" element={<ConfirmPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
