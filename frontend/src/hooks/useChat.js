import { useCallback, useState } from 'react';
import { chatAPI } from '../api/client';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim()) return;
      setError(null);
      const userMsg = { role: 'user', content: text, id: Date.now() };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const history = messages.map(({ role, content }) => ({ role, content }));
        const { data } = await chatAPI.send(text, history);
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.reply,
            sources: data.sources || [],
            id: Date.now() + 1,
          },
        ]);
      } catch (err) {
        setError(err.message || 'Failed to send message');
      } finally {
        setLoading(false);
      }
    },
    [messages]
  );

  const resetChat = () => {
    setMessages([]);
    setError(null);
  };

  const seedContext = (contextText) => {
    setMessages([
      {
        role: 'user',
        content: `Tell me about: ${contextText}`,
        id: Date.now(),
      },
    ]);
  };

  return { messages, loading, error, sendMessage, resetChat, seedContext };
}
