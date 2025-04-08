export interface Message {
  type: 'user' | 'assistant';
  text: string;
}