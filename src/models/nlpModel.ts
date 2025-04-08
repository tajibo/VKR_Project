import type { Message } from '../types';

const knowledgeBase = {
  keywords: {
    расписание: ['расписание', 'пары', 'занятия', 'лекции'],
    контакты: ['контакт', 'телефон', 'почта', 'email', 'связаться'],
    библиотека: ['библиотека', 'книги', 'учебники', 'материалы'],
    экзамены: ['экзамен', 'сессия', 'зачет', 'тест'],
    общие: ['привет', 'здравствуйте', 'пока', 'спасибо']
  },
  
  responses: {
    расписание: 'Расписание занятий доступно в личном кабинете студента. К сожалению, сейчас я не могу показать его напрямую, так как работаю в демо-режиме.',
    контакты: 'Контактная информация университета:\nТелефон: +7 (495) 500-03-63\nE-mail: info@muiv.ru\nАдрес: 115432, г. Москва, 2-й Кожуховский проезд, д. 12, стр. 1',
    библиотека: 'Электронная библиотека университета содержит более 10,000 учебных материалов. Для доступа необходимо авторизоваться через личный кабинет.',
    экзамены: 'Информация о сессии и расписание экзаменов публикуется в личном кабинете за месяц до начала сессии.',
    общие: 'Я виртуальный ассистент Московского университета имени С.Ю. Витте. Чем могу помочь?',
    unknown: 'Извините, я не совсем понял ваш вопрос. Можете, пожалуйста, переформулировать его?'
  }
};
function categorizeMessage(message: string): string {
  const lowercaseMessage = message.toLowerCase();
  
  for (const [category, keywords] of Object.entries(knowledgeBase.keywords)) {
    if (keywords.some(keyword => lowercaseMessage.includes(keyword))) {
      return category;
    }
  }
  return 'unknown';
}

async function neuralNetworkResponse(message: string): Promise<string> {
  const API_URL = "https://api-inference.huggingface.co/models/sberbank-ai/rugpt3small_based_on_gpt2";
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        inputs: message,
        parameters: {
          max_length: 100,
          do_sample: true,
          top_p: 0.95,
          top_k: 50
        }
      })
    });
    const data = await response.json();
    
    if (Array.isArray(data) && data[0].generated_text) {
      return data[0].generated_text;
    }
    return "Извините, я не смог сгенерировать ответ.";
  } catch (error) {
    console.error("Ошибка при вызове нейронной сети:", error);
    return "Извините, произошла ошибка при обработке запроса.";
  }
}

export async function processMessage(message: string): Promise<string> {
  const category = categorizeMessage(message);
  if (category === 'unknown') {
    return await neuralNetworkResponse(message);
  } else {
    return knowledgeBase.responses[category as keyof typeof knowledgeBase.responses];
  }
}

export function getInitialGreeting(): string {
  return 'Здравствуйте! Я ваш персональный ассистент Московского университета имени С.Ю. Витте. Чем могу помочь?';
}
