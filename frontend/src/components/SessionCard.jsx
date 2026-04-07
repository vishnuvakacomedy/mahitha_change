import styles from './SessionCard.module.css'

export default function SessionCard({ session, onClick }) {
  return (
    <div className={styles.card} onClick={onClick} role="button" tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onClick()}>
      <div className={styles.info}>
        <h3 className={styles.title}>{session.title}</h3>
        <p className={styles.description}>{session.description}</p>
        <div className={styles.meta}>
          <span className={styles.badge}>{session.duration_minutes} min</span>
          <span className={styles.badge}>{session.meeting_type}</span>
          <span className={styles.badgeFree}>
            {session.price === 0 ? 'Complimentary' : `$${session.price}`}
          </span>
        </div>
      </div>
      <button className={styles.btn}>Book →</button>
    </div>
  )
}
