import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { PaperAirplaneIcon, PlusIcon } from '@heroicons/react/24/outline';
import ChatMessage from '../components/ChatMessage';
import HaliteLogo from '../components/HaliteLogo';
import BrandName from '../components/BrandName';
import { useChat } from '../hooks/useChat';

export default function Chat() {
  const { messages, loading, error, sendMessage, resetChat, seedContext } = useChat();
  const [input, setInput] = useState('');
  const bottomRef = useRef();
  const location = useLocation();

  useEffect(() => {
    if (location.state?.prefill) {
      seedContext(location.state.prefill);
      window.history.replaceState({}, '');
    }
  }, [location.state, seedContext]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-theme px-6 py-4">
        <div className="flex items-center gap-4">
          <HaliteLogo className="h-10 w-10" />
          <div>
            <h2 className="font-brand text-xl text-primary">
              Ask <BrandName className="text-accent" />
            </h2>
            <p className="font-sans text-sm text-secondary">
              AI chat grounded in your project knowledge graph
            </p>
          </div>
        </div>
        <button onClick={resetChat} className="halite-btn-ghost">
          <PlusIcon className="h-4 w-4" />
          New Chat
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <HaliteLogo className="h-24 w-24" />
            <h3 className="font-brand mt-6 text-lg text-primary">What would you like to know?</h3>
            <p className="mt-2 max-w-md font-sans text-sm text-secondary">
              Ask about architectural decisions, components, or reasoning behind your codebase.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {[
                'Why did we choose JWT over sessions?',
                'What database are we using and why?',
                'What components depend on AuthModule?',
              ].map((q) => (
                <button key={q} onClick={() => sendMessage(q)} className="halite-btn-ghost text-xs">
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {loading && (
              <div className="flex items-center gap-2 font-sans text-sm text-accent">
                <div className="h-2 w-2 animate-pulse rounded-full bg-accent" />
                <BrandName className="text-accent" /> is thinking…
              </div>
            )}
            {error && <p className="font-sans text-sm text-red-400">{error}</p>}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-theme p-4">
        <div className="mx-auto flex max-w-3xl gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about a decision, component, or architectural choice…"
            className="halite-input flex-1"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()} className="halite-btn-primary">
            <PaperAirplaneIcon className="h-4 w-4" />
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
