// /src/pages/api/chat.js

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' })
  }

  const { question } = req.body
  if (!question) {
    return res.status(400).json({ message: 'No question provided' })
  }

  // отправляем в predict то же поле, но называем его text
  const response = await fetch('http://localhost:8000/predict/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: question }),
  })

  if (!response.ok) {
    const err = await response.text()
    return res.status(response.status).json({ message: err })
  }

  const data = await response.json()
  return res.status(200).json(data)
}
