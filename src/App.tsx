import React, { useState, useRef, useEffect } from 'react';
import { Brain, Mic, Send, Settings, HelpCircle } from 'lucide-react';
import { processMessage, getInitialGreeting } from './models/nlpModel';
import type { Message } from './types';

function App() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { type: 'assistant', text: getInitialGreeting() }
  ]);
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (message.trim()) {
      const userMessage = { type: 'user' as const, text: message };
      setMessages(prev => [...prev, userMessage]);
      
      // Обработка сообщения через модель
      const response = processMessage(message);
      setTimeout(() => {
        setMessages(prev => [...prev, {
          type: 'assistant',
          text: response
        }]);
      }, 500);
      
      setMessage('');
    }
  };

  const handleVoice = () => {
    if ('webkitSpeechRecognition' in window) {
      setIsListening(!isListening);
      // Здесь будет реализация распознавания речи
      alert('Функция голосового ввода будет доступна в следующей версии');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-green-400 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-blue-600 p-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Brain className="text-white w-8 h-8" />
            <h1 className="text-white text-xl font-bold">Персональный ассистент МУИВ</h1>
          </div>
          <div className="flex space-x-2">
            <button 
              className="p-2 hover:bg-blue-700 rounded-full transition-colors"
              title="Справка"
            >
              <HelpCircle className="text-white w-6 h-6" />
            </button>
            <button 
              className="p-2 hover:bg-blue-700 rounded-full transition-colors"
              title="Настройки"
            >
              <Settings className="text-white w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="h-[500px] overflow-y-auto p-4 space-y-4">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] p-3 rounded-xl ${
                  msg.type === 'user'
                    ? 'bg-green-500 text-white rounded-br-none'
                    : 'bg-blue-500 text-white rounded-bl-none'
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="flex space-x-2">
            <button
              onClick={handleVoice}
              className={`p-3 rounded-full transition-colors ${
                isListening ? 'bg-red-500' : 'bg-blue-500'
              } text-white hover:opacity-90`}
              title="Голосовой ввод"
            >
              <Mic className="w-6 h-6" />
            </button>
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Введите ваше сообщение..."
              className="flex-1 p-3 rounded-xl border border-gray-300 focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={handleSend}
              className="p-3 bg-green-500 rounded-full text-white hover:opacity-90 transition-colors"
              title="Отправить сообщение"
            >
              <Send className="w-6 h-6" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;