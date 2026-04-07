import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSessions } from '../api'
import styles from './LandingPage.module.css'

export default function LandingPage() {
  const [sessions, setSessions] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    getSessions().then(setSessions).catch(() => setSessions([]))
  }, [])

  return (
    <div className={styles.page}>

      {/* ── Hero ── */}
      <header className={styles.hero}>
        <div className={styles.heroText}>
          <p className={styles.eyebrow}>1-on-1 · 60 Minutes · $80</p>
          <h1 className={styles.headline}>
            A Clarity Session to<br />Quiet the Mental Noise
          </h1>
          <p className={styles.subheadline}>
            If one unresolved decision is quietly draining your energy,
            this session is designed to reset your thinking — in a confidential,
            judgment-free space.
          </p>
          {sessions.length > 0 && (
            <button
              className={styles.ctaBtn}
              onClick={() => navigate(`/book/${sessions[0].id}`)}
            >
              Book Your Session
            </button>
          )}
        </div>
        <div className={styles.heroImage}>
          <img src="/imgs/mahitha.avif" alt="Mahitha Vaka" />
        </div>
      </header>

      {/* ── What this is ── */}
      <section className={styles.section}>
        <div className={styles.sectionInner}>
          <h2 className={styles.sectionTitle}>What This Session Is</h2>
          <p className={styles.sectionLead}>
            This is not advice. This is not therapy.<br />
            <strong>This is structured thinking under psychological safety.</strong>
          </p>
          <div className={styles.pillars}>
            <div className={styles.pillar}>
              <span className={styles.pillarIcon}>🧭</span>
              <h3>Identify the Real Conflict</h3>
              <p>We slow down the noise to find what's actually creating tension — not just the surface-level problem.</p>
            </div>
            <div className={styles.pillar}>
              <span className={styles.pillarIcon}>🔍</span>
              <h3>Separate Facts from Fears</h3>
              <p>Many blocks are rooted in perception, not reality. Together, we examine what's true versus what's a story.</p>
            </div>
            <div className={styles.pillar}>
              <span className={styles.pillarIcon}>🌱</span>
              <h3>Create a Grounded Next Step</h3>
              <p>You leave with one clear, honest next step — not a 10-point plan, just the one thing that matters.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── For you / Not for you ── */}
      <section className={`${styles.section} ${styles.sectionAlt}`}>
        <div className={styles.sectionInner}>
          <div className={styles.twoCol}>
            <div className={styles.forYou}>
              <h2 className={styles.sectionTitle}>This Is For You If…</h2>
              <ul className={styles.checkList}>
                <li>You look fine on the outside but feel heavy on the inside</li>
                <li>One decision keeps cycling through your mind without resolution</li>
                <li>You're high-functioning but privately exhausted by overthinking</li>
                <li>You want a structured space to think — not to be told what to do</li>
                <li>You're ready to slow down long enough to hear yourself clearly</li>
              </ul>
            </div>
            <div className={styles.notForYou}>
              <h2 className={styles.sectionTitle}>This Is Not For You If…</h2>
              <ul className={styles.crossList}>
                <li>You're looking for a quick fix or a magic answer</li>
                <li>You want someone to make the decision for you</li>
                <li>You're seeking therapy or clinical mental health support</li>
                <li>You're not open to honest self-reflection</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── About ── */}
      <section className={styles.section}>
        <div className={styles.sectionInner}>
          <div className={styles.aboutLayout}>
            <img src="/imgs/mahitha.avif" alt="Mahitha Vaka" className={styles.aboutImg} />
            <div className={styles.aboutText}>
              <p className={styles.eyebrow}>About Your Coach</p>
              <h2 className={styles.sectionTitle}>Mahitha Vaka</h2>
              <p>
                Mahitha is a certified life and mindset coach trained in the ICF coaching framework.
                Her approach is reflective and structured rather than directive — she believes that
                lasting change begins when mental noise quiets and self-trust returns.
              </p>
              <p style={{ marginTop: '1rem' }}>
                With a background in helping driven individuals navigate major life transitions,
                Mahitha creates a grounded, judgment-free space where clarity can emerge naturally.
                She doesn't tell you what to do. She helps you hear what you already know.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Offer + Book CTA ── */}
      <section className={`${styles.section} ${styles.offerSection}`}>
        <div className={styles.sectionInner}>
          <div className={styles.offerCard}>
            <div className={styles.offerDetails}>
              <p className={styles.eyebrow}>The Session</p>
              <h2 className={styles.offerTitle}>Clarity Session with Mahitha Vaka</h2>
              <div className={styles.offerMeta}>
                <span>⏱ 60 minutes</span>
                <span>💻 Zoom</span>
                <span>💰 $80</span>
              </div>
              <p className={styles.offerDesc}>
                One focused hour to untangle what's been weighing on you.
                You'll leave with clarity, not confusion.
              </p>
            </div>
            {sessions.length > 0 && (
              <button
                className={styles.ctaBtn}
                onClick={() => navigate(`/book/${sessions[0].id}`)}
              >
                Schedule Your Session →
              </button>
            )}
          </div>
        </div>
      </section>

      <footer className={styles.footer}>
        <p>© {new Date().getFullYear()} Mahitha Vaka ·
          <a href="https://mahithavaka.com"> mahithavaka.com</a>
        </p>
      </footer>
    </div>
  )
}
