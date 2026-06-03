"use client";

import { useState, useRef, useEffect } from 'react';
import { 
  Mic, 
  Send, 
  Download, 
  RefreshCw, 
  Volume2, 
  Loader2,
  Menu,
  Plus,
  MessageSquare,
  Trash2,
  HelpCircle,
  Settings,
  Sparkles,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: number;
}

const SUGGESTION_CARDS = [
  {
    title: "Summarize News",
    desc: "Get a bullet-point summary of the latest national & international events.",
    prompt: "Summarize today's major news and current affairs."
  },
  {
    title: "Daily Quiz",
    desc: "Test my knowledge with 5 multiple-choice questions on recent news.",
    prompt: "Generate a 5-question current affairs quiz based on the latest news."
  },
  {
    title: "Economic Reforms",
    desc: "Explain the latest policy changes, budget updates, and financial reforms.",
    prompt: "Explain the key economic reforms and policy changes from today's news."
  },
  {
    title: "SSC CGL Strategy",
    desc: "How should I prepare current affairs for the upcoming SSC examinations?",
    prompt: "Provide a study plan and strategy to prepare current affairs for the SSC CGL exam."
  }
];

export default function Dashboard() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load chat sessions from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('karma_flow_sessions');
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as ChatSession[];
        setSessions(parsed);
        if (parsed.length > 0) {
          setCurrentSessionId(parsed[0].id);
          setMessages(parsed[0].messages);
        } else {
          createNewSession();
        }
      } catch (e) {
        console.error("Error loading sessions", e);
        createNewSession();
      }
    } else {
      createNewSession();
    }
  }, []);

  // Setup Web Speech API (STT)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = false;
        recognitionRef.current.interimResults = false;

        recognitionRef.current.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          setInput(transcript);
          setIsListening(false);
        };

        recognitionRef.current.onerror = () => setIsListening(false);
        recognitionRef.current.onend = () => setIsListening(false);
      }
    }
  }, []);

  const createNewSession = () => {
    const newId = Date.now().toString();
    const newSession: ChatSession = {
      id: newId,
      title: "New Chat",
      messages: [],
      updatedAt: Date.now()
    };
    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newId);
    setMessages([]);

    const stored = localStorage.getItem('karma_flow_sessions');
    const existing = stored ? JSON.parse(stored) : [];
    localStorage.setItem('karma_flow_sessions', JSON.stringify([newSession, ...existing]));
  };

  const selectSession = (id: string) => {
    const session = sessions.find(s => s.id === id);
    if (session) {
      setCurrentSessionId(id);
      setMessages(session.messages);
      // Close sidebar on mobile
      if (window.innerWidth < 768) {
        setSidebarOpen(false);
      }
    }
  };

  const deleteSession = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = sessions.filter(s => s.id !== id);
    setSessions(updated);
    localStorage.setItem('karma_flow_sessions', JSON.stringify(updated));

    if (currentSessionId === id) {
      if (updated.length > 0) {
        setCurrentSessionId(updated[0].id);
        setMessages(updated[0].messages);
      } else {
        const newId = Date.now().toString();
        const newSession = {
          id: newId,
          title: "New Chat",
          messages: [],
          updatedAt: Date.now()
        };
        setSessions([newSession]);
        setCurrentSessionId(newId);
        setMessages([]);
        localStorage.setItem('karma_flow_sessions', JSON.stringify([newSession]));
      }
    }
  };

  const toggleListen = () => {
    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Chat Submission
  const handleSend = async (e?: React.FormEvent, overrideText?: string) => {
    e?.preventDefault();
    const textToSend = overrideText || input;
    if (!textToSend.trim() || isLoading) return;

    const userText = textToSend.trim();
    if (!overrideText) setInput('');

    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: userText
    };

    const updatedMessages = [...messages, newUserMessage];
    setMessages(updatedMessages);
    setIsLoading(true);

    let activeSessionId = currentSessionId;
    if (!activeSessionId) {
      activeSessionId = Date.now().toString();
      setCurrentSessionId(activeSessionId);
    }

    let sessionTitle = sessions.find(s => s.id === activeSessionId)?.title || "New Chat";
    if (sessionTitle === "New Chat") {
      sessionTitle = userText.length > 30 ? userText.slice(0, 30) + "..." : userText;
    }

    setSessions(prev => {
      const updated = prev.map(s => {
        if (s.id === activeSessionId) {
          return {
            ...s,
            title: sessionTitle,
            messages: updatedMessages,
            updatedAt: Date.now()
          };
        }
        return s;
      });
      localStorage.setItem('karma_flow_sessions', JSON.stringify(updated));
      return updated;
    });

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userText })
      });
      const data = await res.json();
      
      const newAssistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer 
      };

      const finalMessages = [...updatedMessages, newAssistantMessage];
      setMessages(finalMessages);

      setSessions(prev => {
        const updated = prev.map(s => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              messages: finalMessages,
              updatedAt: Date.now()
            };
          }
          return s;
        });
        localStorage.setItem('karma_flow_sessions', JSON.stringify(updated));
        return updated;
      });
    } catch (error) {
      console.error(error);
      const errorMsg: Message = { 
        id: (Date.now() + 2).toString(), 
        role: 'assistant', 
        content: 'Connection error while reaching the AI.' 
      };
      const finalMessages = [...updatedMessages, errorMsg];
      setMessages(finalMessages);

      setSessions(prev => {
        const updated = prev.map(s => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              messages: finalMessages,
              updatedAt: Date.now()
            };
          }
          return s;
        });
        localStorage.setItem('karma_flow_sessions', JSON.stringify(updated));
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Play TTS
  const playTTS = async (text: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/media/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const blob = await res.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audio.play();
    } catch (e) {
      console.error("Audio error", e);
    }
  };

  const triggerIngestion = async () => {
    setIsIngesting(true);
    try {
      await fetch(`${BACKEND_URL}/api/ingest/trigger`, { method: 'POST' });
    } finally {
      setTimeout(() => setIsIngesting(false), 2000);
    }
  };

  return (
    <div suppressHydrationWarning className="flex h-screen bg-[#070913] text-slate-100 font-sans selection:bg-indigo-500/30 overflow-hidden">
      
      {/* MOBILE OVERLAY */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* COLLAPSIBLE SIDEBAR */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-72 bg-[#0c0e1a] border-r border-slate-900 flex flex-col transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        
        {/* SIDEBAR HEADER */}
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 via-indigo-500 to-purple-500 flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.25)]">
              <Sparkles className="text-white w-4 h-4" />
            </div>
            <span className="font-bold text-sm bg-clip-text text-transparent bg-gradient-to-r from-indigo-200 to-white">KarmaaFlow AI</span>
          </div>
          <button 
            onClick={() => setSidebarOpen(false)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 md:flex hidden"
            title="Collapse menu"
          >
            <Menu className="w-4 h-4" />
          </button>
        </div>

        {/* NEW CHAT BUTTON */}
        <div className="px-4 py-2">
          <button 
            onClick={createNewSession}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:border-slate-700 text-[#c4c7c5] hover:text-[#e3e3e3] font-medium text-sm transition-all duration-200 shadow-md group"
          >
            <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform duration-200" />
            New Chat
          </button>
        </div>

        {/* CHAT SESSIONS LIST */}
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
          <div className="px-3 mb-2 text-xs font-semibold text-slate-500 tracking-wider">
            Recent
          </div>
          {sessions.map((sess) => (
            <div 
              key={sess.id}
              onClick={() => selectSession(sess.id)}
              className={`group flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition text-sm ${sess.id === currentSessionId ? 'bg-slate-900 text-indigo-400 font-medium' : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'}`}
            >
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <MessageSquare className={`w-4 h-4 flex-shrink-0 ${sess.id === currentSessionId ? 'text-indigo-400' : 'text-slate-500'}`} />
                <span className="truncate">{sess.title}</span>
              </div>
              <button 
                onClick={(e) => deleteSession(sess.id, e)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-red-400 transition flex-shrink-0 ml-1"
                title="Delete chat"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>

        {/* SIDEBAR FOOTER */}
        <div className="p-4 border-t border-slate-900/80 space-y-1">
          <div className="flex items-center gap-3 px-3 py-2 text-sm text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-900/50 cursor-pointer transition">
            <HelpCircle className="w-4 h-4 text-slate-500" />
            <span>Help & Support</span>
          </div>
          <div className="flex items-center gap-3 px-3 py-2 text-sm text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-900/50 cursor-pointer transition">
            <Settings className="w-4 h-4 text-slate-500" />
            <span>Settings</span>
          </div>
        </div>

      </aside>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden bg-[#070913]">
        
        {/* HEADER */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-slate-900 bg-[#070913]/90 backdrop-blur-md z-30">
          <div className="flex items-center gap-4">
            {!sidebarOpen && (
              <button 
                onClick={() => setSidebarOpen(true)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900 transition"
                title="Expand menu"
              >
                <Menu className="w-5 h-5" />
              </button>
            )}
            <div className="md:block hidden">
              <span className="text-xs text-slate-500 uppercase tracking-widest font-semibold">SSC current affairs</span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button 
              onClick={triggerIngestion}
              disabled={isIngesting}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-full bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 hover:text-white transition disabled:opacity-50 shadow-sm"
            >
              {isIngesting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
              Refresh News
            </button>
            <a 
              href={`${BACKEND_URL}/api/media/pdf`}
              target="_blank"
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-full bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-650 hover:from-indigo-500 hover:to-purple-500 text-white transition shadow-[0_0_12px_rgba(99,102,241,0.25)]"
            >
              <Download className="w-3.5 h-3.5" />
              Daily PDF
            </a>
          </div>
        </header>

        {/* CHAT/LANDING WRAPPER */}
        <main className="flex-1 overflow-y-auto flex flex-col justify-between">
          
          {messages.length === 0 ? (
            // LANDING PAGE
            <div className="flex-1 flex flex-col justify-center max-w-3xl mx-auto w-full px-6 md:px-0 py-8">
              <motion.div 
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="mb-8"
              >
                <h1 className="text-4xl md:text-5xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-500 pb-2">
                  Hello, Scholar
                </h1>
                <h2 className="text-3xl md:text-4xl font-bold text-slate-500">
                  How can I help you today?
                </h2>
                <p className="mt-4 text-slate-400 text-sm max-w-xl leading-relaxed">
                  I am your AI Current Affairs Tutor for the SSC Exam. I analyze daily news updates, retrieve context, and provide focused answers to aid your learning.
                </p>
              </motion.div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                {SUGGESTION_CARDS.map((card, i) => (
                  <motion.div 
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: i * 0.1 }}
                    key={i}
                    onClick={() => handleSend(undefined, card.prompt)}
                    className="group relative bg-[#0c0e1a] border border-slate-900 hover:border-slate-800/80 p-5 rounded-2xl cursor-pointer transition-all duration-300 hover:bg-slate-900/40 flex flex-col justify-between min-h-[120px]"
                  >
                    <div>
                      <h3 className="font-semibold text-slate-200 group-hover:text-indigo-400 transition-colors text-sm flex items-center gap-2">
                        {card.title}
                      </h3>
                      <p className="text-xs text-slate-500 mt-2 leading-relaxed">{card.desc}</p>
                    </div>
                    <div className="self-end mt-2 p-1.5 rounded-full bg-[#070913] border border-slate-900 text-slate-500 group-hover:text-indigo-400 group-hover:border-indigo-500/20 transition-all duration-300">
                      <Plus className="w-3.5 h-3.5" />
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          ) : (
            // MESSAGE STREAM
            <div className="flex-1 overflow-y-auto px-6 md:px-0 py-6 space-y-8 scroll-smooth max-w-3xl mx-auto w-full">
              {messages.map((msg) => (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={msg.id} 
                  className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} group`}
                >
                  {msg.role === 'user' ? (
                    <div className="max-w-[85%] px-5 py-3 rounded-2xl rounded-tr-sm bg-slate-900 border border-slate-800 text-slate-200 shadow-md">
                      <p className="whitespace-pre-wrap text-[14px] leading-relaxed">{msg.content}</p>
                    </div>
                  ) : (
                    <div className="w-full flex gap-4 items-start">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 via-indigo-500 to-purple-500 flex items-center justify-center flex-shrink-0 shadow-[0_0_10px_rgba(99,102,241,0.2)] mt-0.5">
                        <Sparkles className="w-4 h-4 text-white animate-pulse" />
                      </div>
                      <div className="flex-1 space-y-2">
                        <div className="text-slate-200 text-[15px] leading-relaxed whitespace-pre-wrap">
                          {msg.content}
                        </div>
                        
                        <div className="flex items-center gap-3 pt-1 text-slate-500">
                          <button 
                            onClick={() => playTTS(msg.content)}
                            className="p-1 rounded hover:text-slate-300 hover:bg-slate-900 transition flex items-center gap-1 text-xs font-semibold"
                            title="Listen"
                          >
                            <Volume2 className="w-3.5 h-3.5" />
                            <span>Listen</span>
                          </button>
                          <button 
                            onClick={() => handleCopy(msg.content, msg.id)}
                            className="p-1 rounded hover:text-slate-300 hover:bg-slate-900 transition flex items-center gap-1 text-xs font-semibold"
                            title="Copy"
                          >
                            {copiedId === msg.id ? (
                              <>
                                <Check className="w-3.5 h-3.5 text-emerald-500" />
                                <span className="text-emerald-500">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3.5 h-3.5" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                          <button className="p-1 rounded hover:text-slate-300 hover:bg-slate-900 transition">
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button className="p-1 rounded hover:text-slate-300 hover:bg-slate-900 transition">
                            <ThumbsDown className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}
              
              {isLoading && (
                <div className="w-full flex gap-4 items-start">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 via-indigo-500 to-purple-500 flex items-center justify-center flex-shrink-0 shadow-[0_0_10px_rgba(99,102,241,0.2)] mt-0.5 animate-pulse">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1 space-y-3 pt-1">
                    <div className="h-3.5 bg-slate-900 rounded-full w-3/4 animate-shimmer"></div>
                    <div className="h-3.5 bg-slate-900 rounded-full w-5/6 animate-shimmer"></div>
                    <div className="h-3.5 bg-slate-900 rounded-full w-1/2 animate-shimmer"></div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* INPUT CONTAINER */}
          <footer className="p-4 md:p-6 bg-gradient-to-t from-[#070913] via-[#070913] to-transparent pt-4">
            <div className="max-w-3xl mx-auto">
              <form onSubmit={handleSend} className="relative flex items-center bg-[#0c0e1a] border border-slate-900/80 focus-within:border-slate-800/80 rounded-2xl p-1.5 shadow-2xl transition">
                <button 
                  type="button" 
                  onClick={toggleListen}
                  className={`p-3 rounded-xl transition ${isListening ? 'bg-red-500/10 text-red-500 animate-pulse' : 'text-slate-500 hover:bg-slate-900 hover:text-slate-200'}`}
                  title={isListening ? "Listening..." : "Voice input"}
                >
                  <Mic className="w-4 h-4" />
                </button>
                <input 
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about today's current affairs..."
                  className="flex-1 bg-transparent border-none text-slate-200 placeholder:text-slate-600 focus:outline-none px-4 py-2.5 text-sm"
                />
                <button 
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="p-3 bg-gradient-to-tr from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl transition disabled:opacity-30 flex-shrink-0"
                  title="Send message"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
              <div className="mt-2.5 text-center">
                <span className="text-[10px] text-slate-600">KarmaaFlow AI can make mistakes. Verify important info.</span>
              </div>
            </div>
          </footer>

        </main>
      </div>

    </div>
  );
}
