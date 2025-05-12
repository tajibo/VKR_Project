import Link from 'next/link'

export default function Home() {
  return (
    <main style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Интеллектуальный Ассистент Витте</h1>
      <p>Ваш помощник в учебе и поддержке студентов МУ Витте.</p>
      <Link
        href="/predict"
        style={{
          display: 'inline-block',
          marginTop: '1rem',
          padding: '0.75rem 1.5rem',
          background: '#0070f3',
          color: '#fff',
          borderRadius: '4px',
          textDecoration: 'none'
        }}>
        
          Задать вопрос
        
      </Link>
    </main>
  );
}
