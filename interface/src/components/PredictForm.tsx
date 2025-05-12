import { useState, FormEvent } from 'react'

interface PredictFormProps {
  endpoint?: string
}

export default function PredictForm({ endpoint = '/api/predict' }: PredictFormProps) {
  const [text, setText] = useState('')
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!text.trim()) {
      setError('Введите текст запроса')
      return
    }
    setError(null)
    setLoading(true)

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        redirect: 'manual',
      })

      console.log('Fetch status:', res.status, res.statusText)

      if (res.status === 307 || res.status === 308) {
        // Follow redirect manually
        const location = res.headers.get('location') || ''
        return handleRedirect(location)
      }

      if (!res.ok) {
        const data = await res.json().catch(() => null)
        const detail = data?.detail || data?.message || 'Ошибка сервера'
        throw new Error(detail)
      }

      const data = await res.json()
      setResult(data.intent)
    } catch (err: any) {
      console.error('Fetch error:', err)
      setError(err.message || 'Неизвестная ошибка')
    } finally {
      setLoading(false)
    }
  }

  const handleRedirect = async (location: string) => {
    try {
      const redirected = await fetch(location, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (!redirected.ok) {
        const data = await redirected.json().catch(() => null)
        const detail = data?.detail || data?.message || 'Ошибка сервера'
        throw new Error(detail)
      }
      const data = await redirected.json()
      setResult(data.intent)
    } catch (err: any) {
      console.error('Redirect fetch error:', err)
      setError(err.message || 'Неизвестная ошибка при редиректе')
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 600, margin: '0 auto' }}>
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        rows={5}
        placeholder="Введите ваш вопрос..."
        style={{ width: '100%', padding: '8px', fontSize: '1rem' }}
      />
      <button type="submit" disabled={loading} style={{ marginTop: '8px', padding: '8px 16px' }}>
        {loading ? 'Обработка...' : 'Получить ответ'}
      </button>

      {error && <p style={{ color: 'red', marginTop: '8px' }}>{error}</p>}

      {result && (
        <div style={{ marginTop: '16px' }}>
          <h3>Ответ ассистента:</h3>
          <p>{result}</p>
        </div>
      )}
    </form>
  )
}
