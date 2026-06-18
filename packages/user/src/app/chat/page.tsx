'use client';

import { useState, useEffect, useRef } from 'react';
import {
    Send,
    Bot,
    User,
    Loader2,
    Sparkles,
    Trash2,
    ThumbsUp,
    ThumbsDown,
    AlertCircle,
    Info,
    Calendar,
    MapPin,
    Search,
    Star,
    ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface VendorService {
    id: string;
    name: string;
    price_min?: number;
    price_max?: number;
}

interface VendorSuggestion {
    id: string;
    business_name: string;
    city?: string;
    rating?: number;
    total_reviews?: number;
    price_min?: number;
    price_max?: number;
    services?: VendorService[];
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    agent_name?: string;
    timestamp: Date;
    is_streaming?: boolean;
    feedback?: 'up' | 'down' | null;
    vendors?: VendorSuggestion[];
}

const AGENT_COLORS: Record<string, string> = {
    'TriageAgent': 'bg-blue-100 text-blue-700 border-blue-200',
    'EventPlannerAgent': 'bg-purple-100 text-purple-700 border-purple-200',
    'VendorDiscoveryAgent': 'bg-green-100 text-green-700 border-green-200',
    'BookingAgent': 'bg-amber-100 text-amber-700 border-amber-200',
    'OrchestratorAgent': 'bg-indigo-100 text-indigo-700 border-indigo-200',
};

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const [activeAgent, setActiveAgent] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [sessionId, setSessionId] = useState<string | null>(null);
    
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Load session from localStorage on mount
    useEffect(() => {
        const savedMessages = localStorage.getItem('ai_chat_history');
        const savedSessionId = localStorage.getItem('ai_chat_session_id');
        
        if (savedMessages) {
            try {
                const parsed = JSON.parse(savedMessages) as Array<Omit<Message, 'timestamp'> & { timestamp: string }>;
                setMessages(parsed.map((m) => ({
                    ...m,
                    timestamp: new Date(m.timestamp)
                })));
            } catch (e) {
                console.error("Failed to parse saved messages", e);
            }
        }
        
        if (savedSessionId) {
            setSessionId(savedSessionId);
        } else {
            const newId = Math.random().toString(36).substring(7);
            setSessionId(newId);
            localStorage.setItem('ai_chat_session_id', newId);
        }
    }, []);

    // Save messages to localStorage when updated
    useEffect(() => {
        if (messages.length > 0) {
            localStorage.setItem('ai_chat_history', JSON.stringify(messages));
        }
    }, [messages]);

    // Scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value);
        // Auto-resize
        e.target.style.height = 'inherit';
        e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
    };

    const clearChat = () => {
        if (window.confirm('Are you sure you want to clear the chat history?')) {
            setMessages([]);
            localStorage.removeItem('ai_chat_history');
            const newId = Math.random().toString(36).substring(7);
            setSessionId(newId);
            localStorage.setItem('ai_chat_session_id', newId);
        }
    };

    const handleFeedback = async (messageId: string, type: 'up' | 'down') => {
        const message = messages.find(m => m.id === messageId);
        if (!message || message.feedback === type) return;

        try {
            // Update UI optimistically
            setMessages(prev => prev.map(m => 
                m.id === messageId ? { ...m, feedback: type } : m
            ));

            // Call feedback API via proxy
            await fetch('/api/ai/feedback', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message_id: messageId, feedback: type }) 
            });
        } catch (e) {
            console.error("Failed to send feedback", e);
        }
    };

    const sendMessage = async () => {
        if (!input.trim() || isStreaming) return;

        const userMessage: Message = {
            id: Math.random().toString(36).substring(7),
            role: 'user',
            content: input.trim(),
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsStreaming(true);
        setError(null);
        setActiveAgent('TriageAgent');

        const assistantMessageId = Math.random().toString(36).substring(7);
        const assistantMessage: Message = {
            id: assistantMessageId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            is_streaming: true,
        };

        setMessages(prev => [...prev, assistantMessage]);

        try {
            const response = await fetch('/api/ai/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: userMessage.content,
                    session_id: sessionId,
                }),
            });

            if (!response.ok) throw new Error('Failed to connect to AI assistant');

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let accumulatedContent = '';

            if (!reader) throw new Error('No stream reader available');

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.trim() || !line.startsWith('data: ')) continue;
                    
                    const dataStr = line.substring(6);
                    if (dataStr === '[DONE]') break;

                    try {
                        const data = JSON.parse(dataStr);
                        
                        if (data.token) {
                            accumulatedContent += data.token;
                            setMessages(prev => prev.map(m => 
                                m.id === assistantMessageId 
                                    ? { ...m, content: accumulatedContent } 
                                    : m
                            ));
                        }
                        
                        if (data.agent) {
                            setActiveAgent(data.agent);
                        }

                        if (data.vendors && Array.isArray(data.vendors) && data.vendors.length > 0) {
                            setMessages(prev => prev.map(m =>
                                m.id === assistantMessageId
                                    ? { ...m, vendors: data.vendors as VendorSuggestion[] }
                                    : m
                            ));
                        }

                        if (data.done) {
                            if (data.session_id && !sessionId) {
                                setSessionId(data.session_id);
                                localStorage.setItem('ai_chat_session_id', data.session_id);
                            }
                            break;
                        }

                        if (data.error) {
                            setError(data.error || 'An error occurred during AI processing');
                        }
                    } catch (e) {
                        console.error("Error parsing stream data", e);
                    }
                }
            }

            // Mark streaming as finished
            setMessages(prev => prev.map(m => 
                m.id === assistantMessageId 
                    ? { ...m, is_streaming: false, agent_name: activeAgent || undefined } 
                    : m
            ));

        } catch (err) {
            console.error("Chat error:", err);
            setError(err instanceof Error ? err.message : 'Failed to get a response from the AI assistant.');
            setMessages(prev => prev.filter(m => m.id !== assistantMessageId));
        } finally {
            setIsStreaming(false);
            setActiveAgent(null);
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-6rem)] max-w-5xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white rounded-t-2xl">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-100 rounded-lg">
                        <Sparkles className="h-5 w-5 text-indigo-600" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-gray-900 leading-tight">AI Event Assistant</h1>
                        <p className="text-xs text-gray-500">Powered by Gemini & Multi-Agent Orchestrator</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {isStreaming && (
                        <div className="flex items-center gap-2 px-3 py-1 bg-indigo-50 border border-indigo-100 rounded-full animate-pulse">
                            <Loader2 className="h-3 w-3 animate-spin text-indigo-600" />
                            <span className="text-xs font-medium text-indigo-700">AI is thinking...</span>
                        </div>
                    )}
                    <button 
                        onClick={clearChat}
                        className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        title="Clear History"
                    >
                        <Trash2 className="h-5 w-5" />
                    </button>
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto px-6 py-8 space-y-8 bg-gray-50/50">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center space-y-6 max-w-md mx-auto">
                        <div className="p-4 bg-white rounded-3xl shadow-sm border border-gray-100">
                            <Bot className="h-12 w-12 text-indigo-600" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-gray-900">How can I help you today?</h2>
                            <p className="mt-2 text-gray-500">
                                I can help you plan weddings, find verified vendors, 
                                manage your event timeline, or check availability for services.
                            </p>
                        </div>
                        <div className="grid grid-cols-1 gap-3 w-full">
                            {[
                                { icon: Calendar, text: "Plan a wedding in Lahore for Oct 2026", color: "text-purple-600" },
                                { icon: Search, text: "Find top catering services in Karachi", color: "text-blue-600" },
                                { icon: MapPin, text: "What are the best venues in Islamabad?", color: "text-green-600" }
                            ].map((suggestion, i) => (
                                <button
                                    key={i}
                                    onClick={() => { setInput(suggestion.text); inputRef.current?.focus(); }}
                                    className="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-2xl text-sm font-medium text-gray-700 hover:border-indigo-400 hover:bg-indigo-50 transition-all text-left"
                                >
                                    <suggestion.icon className={cn("h-4 w-4", suggestion.color)} />
                                    {suggestion.text}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <>
                        {messages.map((m) => (
                            <div 
                                key={m.id} 
                                className={cn(
                                    "flex flex-col",
                                    m.role === 'user' ? "items-end" : "items-start"
                                )}
                            >
                                <div className={cn(
                                    "flex items-start gap-3 max-w-[85%]",
                                    m.role === 'user' ? "flex-row-reverse" : "flex-row"
                                )}>
                                    <div className={cn(
                                        "h-9 w-9 rounded-xl flex items-center justify-center shrink-0 shadow-sm border",
                                        m.role === 'user' 
                                            ? "bg-indigo-600 text-white border-indigo-500" 
                                            : "bg-white text-gray-600 border-gray-200"
                                    )}>
                                        {m.role === 'user' ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
                                    </div>
                                    
                                    <div className="space-y-2">
                                        <div className={cn(
                                            "relative px-5 py-4 rounded-2xl text-sm leading-relaxed shadow-sm",
                                            m.role === 'user'
                                                ? "bg-indigo-600 text-white rounded-tr-sm"
                                                : "bg-white text-gray-900 border border-gray-100 rounded-tl-sm"
                                        )}>
                                            {m.content || (
                                                <div className="flex gap-1.5 py-1">
                                                    <span className="h-1.5 w-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                                    <span className="h-1.5 w-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                                    <span className="h-1.5 w-1.5 bg-indigo-400 rounded-full animate-bounce"></span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Feedback + agent badge */}
                                        {m.role === 'assistant' && !m.is_streaming && (
                                            <div className="flex items-center gap-3 pl-1">
                                                <div className="flex items-center gap-1">
                                                    <button
                                                        onClick={() => handleFeedback(m.id, 'up')}
                                                        className={cn(
                                                            "p-1.5 rounded-lg transition-colors",
                                                            m.feedback === 'up' ? "bg-green-100 text-green-600" : "text-gray-400 hover:text-green-600 hover:bg-green-50"
                                                        )}
                                                    >
                                                        <ThumbsUp className="h-3.5 w-3.5" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleFeedback(m.id, 'down')}
                                                        className={cn(
                                                            "p-1.5 rounded-lg transition-colors",
                                                            m.feedback === 'down' ? "bg-red-100 text-red-600" : "text-gray-400 hover:text-red-600 hover:bg-red-50"
                                                        )}
                                                    >
                                                        <ThumbsDown className="h-3.5 w-3.5" />
                                                    </button>
                                                </div>
                                                {m.agent_name && (
                                                    <div className={cn(
                                                        "px-2 py-0.5 border text-[10px] font-bold rounded-md uppercase tracking-wider",
                                                        AGENT_COLORS[m.agent_name] || "bg-gray-100 text-gray-600 border-gray-200"
                                                    )}>
                                                        {m.agent_name.replace('Agent', '')}
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {/* Vendor booking cards */}
                                        {m.role === 'assistant' && !m.is_streaming && m.vendors && m.vendors.length > 0 && (
                                            <div className="mt-1">
                                                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2 pl-1">
                                                    {m.vendors.length} vendor{m.vendors.length > 1 ? 's' : ''} found — tap to book
                                                </p>
                                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-xl">
                                                    {m.vendors.slice(0, 6).map((v) => {
                                                        const firstService = v.services?.find(s => s.id);
                                                        const bookUrl = firstService
                                                            ? `/marketplace/${v.id}/book?serviceId=${firstService.id}&serviceName=${encodeURIComponent(firstService.name)}`
                                                            : `/marketplace/${v.id}`;
                                                        return (
                                                            <div
                                                                key={v.id}
                                                                className="bg-white border border-gray-200 rounded-xl p-3.5 shadow-sm hover:border-indigo-300 hover:shadow-md transition-all"
                                                            >
                                                                <div className="flex items-start justify-between gap-2 mb-1.5">
                                                                    <h4 className="font-semibold text-sm text-gray-900 leading-tight truncate">{v.business_name}</h4>
                                                                    {v.rating != null && v.rating > 0 && (
                                                                        <div className="flex items-center gap-0.5 shrink-0">
                                                                            <Star className="h-3 w-3 text-amber-400 fill-amber-400" />
                                                                            <span className="text-xs font-medium text-gray-700">{v.rating.toFixed(1)}</span>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                                {v.city && (
                                                                    <div className="flex items-center gap-1 mb-1.5">
                                                                        <MapPin className="h-3 w-3 text-gray-400 shrink-0" />
                                                                        <span className="text-xs text-gray-500 truncate">{v.city}</span>
                                                                    </div>
                                                                )}
                                                                {(v.price_min != null || v.price_max != null) && (
                                                                    <p className="text-xs text-indigo-600 font-medium mb-2.5">
                                                                        PKR {v.price_min != null ? v.price_min.toLocaleString() : '?'}
                                                                        {v.price_max != null && ` – ${v.price_max.toLocaleString()}`}
                                                                    </p>
                                                                )}
                                                                <div className="flex gap-1.5">
                                                                    <a
                                                                        href={bookUrl}
                                                                        className="flex-1 text-center py-1.5 px-2 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 transition-colors"
                                                                    >
                                                                        Book Now
                                                                    </a>
                                                                    <a
                                                                        href={`/marketplace/${v.id}`}
                                                                        className="p-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
                                                                        title="View profile"
                                                                    >
                                                                        <ExternalLink className="h-3.5 w-3.5" />
                                                                    </a>
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                        
                        {isStreaming && activeAgent && (
                             <div className="flex items-center gap-3 mt-2 pl-12">
                                <div className={cn(
                                    "px-2.5 py-1 border text-[10px] font-bold rounded-full uppercase tracking-wider flex items-center gap-2",
                                    AGENT_COLORS[activeAgent] || "bg-gray-100 text-gray-600 border-gray-200"
                                )}>
                                    <div className="h-1.5 w-1.5 bg-current rounded-full animate-pulse" />
                                    {activeAgent} Active
                                </div>
                             </div>
                        )}

                        {error && (
                            <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-100 rounded-2xl text-red-800 text-sm max-w-2xl mx-auto mt-4">
                                <AlertCircle className="h-5 w-5 shrink-0" />
                                <p>{error}</p>
                            </div>
                        )}
                        <div ref={messagesEndRef} className="h-4" />
                    </>
                )}
            </div>

            {/* Input Area */}
            <div className="p-6 bg-white border-t border-gray-100 rounded-b-2xl">
                <div className="relative group max-w-4xl mx-auto">
                    <textarea
                        ref={inputRef}
                        rows={1}
                        value={input}
                        onChange={handleInput}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                sendMessage();
                            }
                        }}
                        placeholder="Message our AI assistant..."
                        className="w-full px-5 py-4 bg-gray-50 border border-gray-200 rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all resize-none pr-14"
                        disabled={isStreaming}
                    />
                    <button
                        onClick={sendMessage}
                        disabled={!input.trim() || isStreaming}
                        className={cn(
                            "absolute right-3 bottom-3 p-2.5 rounded-xl transition-all",
                            input.trim() && !isStreaming
                                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-200"
                                : "bg-gray-200 text-gray-400 cursor-not-allowed"
                        )}
                    >
                        {isStreaming ? (
                            <Loader2 className="h-5 w-5 animate-spin" />
                        ) : (
                            <Send className="h-5 w-5" />
                        )}
                    </button>
                </div>
                <div className="flex items-center justify-center gap-4 mt-3 text-[10px] text-gray-400 uppercase tracking-widest font-medium">
                    <div className="flex items-center gap-1.5">
                        <Info className="h-3 w-3" />
                        AI can make mistakes. Verify important info.
                    </div>
                </div>
            </div>
        </div>
    );
}
