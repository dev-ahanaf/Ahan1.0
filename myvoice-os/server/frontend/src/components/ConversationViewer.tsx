import React, { useState, useEffect } from 'react';
import { getConversations, getConversationMessages, deleteConversation } from '../api';
import { ConversationItem, ConversationMessage } from '../types';

export const ConversationViewer: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [selectedConv, setSelectedConv] = useState<ConversationItem | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async (q = '') => {
    try {
      setLoading(true);
      const res = await getConversations(q);
      setConversations(res.conversations);
      if (res.conversations.length > 0 && !selectedConv) {
        selectConversation(res.conversations[0]);
      } else if (res.conversations.length === 0) {
        setSelectedConv(null);
        setMessages([]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const selectConversation = async (conv: ConversationItem) => {
    setSelectedConv(conv);
    try {
      setLoadingMessages(true);
      const res = await getConversationMessages(conv.id);
      setMessages(res.messages);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingMessages(false);
    }
  };

  const handleDelete = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to permanently delete this conversation?')) return;
    try {
      await deleteConversation(convId);
      if (selectedConv?.id === convId) {
        setSelectedConv(null);
        setMessages([]);
      }
      await loadConversations(searchQuery);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadConversations(searchQuery);
  };

  const renderLatencyPills = (providerInfoStr: string | null | undefined, totalMs: number | null | undefined) => {
    if (!totalMs && !providerInfoStr) return null;
    let info: any = {};
    if (providerInfoStr) {
      try {
        info = JSON.parse(providerInfoStr);
      } catch {
        info = {};
      }
    }

    return (
      <div className="flex flex-wrap gap-1.5 mt-2 text-[10px]">
        {totalMs !== null && totalMs !== undefined && (
          <span className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">
            Total: {totalMs}ms
          </span>
        )}
        {info.stt_latency_ms !== undefined && (
          <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-mono">
            STT: {info.stt_latency_ms}ms
          </span>
        )}
        {info.llm_first_token_ms !== undefined && (
          <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">
            LLM TTFT: {info.llm_first_token_ms}ms
          </span>
        )}
        {info.tts_first_audio_ms !== undefined && (
          <span className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono">
            TTS TTFA: {info.tts_first_audio_ms}ms
          </span>
        )}
        {info.asr_provider && (
          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
            {info.asr_provider}
          </span>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-xs overflow-hidden flex flex-col h-[700px]">
      {/* Header bar */}
      <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-4 bg-white/80 dark:bg-slate-900/80 backdrop-blur">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-[#1677ff] border border-blue-200/80 dark:border-blue-800">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </span>
            Conversation Memory Explorer
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Isolated device conversation sessions and real-time response telemetry</p>
        </div>

        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search messages..."
            className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-white placeholder-slate-400 w-56 focus:outline-hidden focus:border-[#1677ff]"
          />
          <button
            type="submit"
            className="text-xs px-3.5 py-1.5 rounded-xl bg-[#1677ff] hover:bg-blue-600 text-white font-medium transition shadow-xs"
          >
            Search
          </button>
        </form>
      </div>

      {/* Main split view */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 overflow-hidden">
        {/* Left column: Conversation list */}
        <div className="border-r border-slate-100 dark:border-slate-800/80 overflow-y-auto bg-slate-50/50 dark:bg-slate-950/30">
          {loading && (
            <div className="p-6 text-center text-xs text-slate-400">Loading conversations...</div>
          )}
          {!loading && conversations.length === 0 && (
            <div className="p-8 text-center text-xs text-slate-400">
              No conversations found. Spoken interactions over WebSocket or HTTP will appear here automatically.
            </div>
          )}
          {conversations.map((c) => {
            const isSelected = selectedConv?.id === c.id;
            return (
              <div
                key={c.id}
                onClick={() => selectConversation(c)}
                className={`p-3.5 border-b border-slate-100 dark:border-slate-800/50 cursor-pointer transition flex items-center justify-between ${
                  isSelected ? 'bg-blue-50 dark:bg-blue-950/40 border-l-2 border-l-[#1677ff]' : 'hover:bg-slate-100/70 dark:hover:bg-slate-800/40'
                }`}
              >
                <div className="overflow-hidden pr-2">
                  <div className="text-xs font-semibold text-slate-900 dark:text-white truncate">{c.title || 'Voice Chat'}</div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono mt-0.5">{c.device_id}</div>
                  <div className="text-[10px] text-slate-400 mt-1">
                    {new Date(c.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {c.message_count} messages
                  </div>
                </div>
                <button
                  onClick={(e) => handleDelete(c.id, e)}
                  title="Delete conversation"
                  className="p-1 rounded text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/20 transition"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>

        {/* Right column: Message transcript */}
        <div className="col-span-2 flex flex-col bg-white dark:bg-slate-900/50 overflow-hidden">
          {selectedConv ? (
            <>
              <div className="px-4 py-2.5 border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-slate-900 dark:text-white">{selectedConv.title}</span>
                  <span className="text-[11px] text-slate-500 dark:text-slate-400 ml-2 font-mono">({selectedConv.device_id})</span>
                </div>
                <span className="text-[10px] text-slate-400">
                  Created: {new Date(selectedConv.created_at).toLocaleString()}
                </span>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {loadingMessages && (
                  <div className="text-center text-xs text-slate-400 py-6">Loading messages...</div>
                )}
                {!loadingMessages && messages.length === 0 && (
                  <div className="text-center text-xs text-slate-400 py-12">No messages in this conversation.</div>
                )}
                {messages.map((m) => {
                  const isUser = m.role === 'user';
                  return (
                    <div
                      key={m.id}
                      className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                    >
                      <div className="text-[10px] text-slate-400 mb-1 flex items-center gap-1.5">
                        <span className="font-semibold uppercase">{m.role}</span>
                        <span>•</span>
                        <span>{new Date(m.created_at).toLocaleTimeString()}</span>
                      </div>
                      <div
                        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs ${
                          isUser
                            ? 'bg-[#1677ff] text-white rounded-br-none shadow-xs'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 rounded-bl-none border border-slate-200/70 dark:border-slate-700/60'
                        }`}
                      >
                        <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                        {!isUser && renderLatencyPills(m.provider_info, m.latency_ms)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400 text-xs">
              Select a conversation on the left to inspect transcripts.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
