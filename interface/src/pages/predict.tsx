import PredictForm from '../components/PredictForm'

export default function PredictPage() {
  return (
    <main style={{ padding: '2rem' }}>
      <h1>Новый вопрос</h1>
      <p>Введите ваш вопрос, и ассистент ответит на него.</p>
      <PredictForm />  {/* по умолчанию /api/predict/ */}
    </main>
  )
}
