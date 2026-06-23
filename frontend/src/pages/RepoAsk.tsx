import { useState, useRef, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Send, Copy, Check } from 'lucide-react';
import { TopBar } from '../components/layout/TopBar';
import { CitationChip } from '../components/qa/CitationChip';
import { client, Claim } from '../api/client';
import './RepoAsk.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  claims?: Claim[];
  status?: 'success' | 'empty_db' | 'no_results' | 'error';
  suggestions?: string[];
  disclaimer?: string;
  source?: string;
  gitHistory?: Array<{ sha: string; short_sha: string; message: string }>;
  jiraIssues?: Array<{ key: string; summary: string; status: string; url: string }>;
  timestamp: number;
}

export function RepoAsk() {
  const { repoId = 'default' } = useParams<{ repoId: string }>();
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedMessage, setExpandedMessage] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Pre-fill input from URL query params (from graph node click)
  useEffect(() => {
    const question = searchParams.get('question');
    if (question) {
      setInput(decodeURIComponent(question));
    }
  }, [searchParams]);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const copyToClipboard = (text: string, messageId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(messageId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };

    const question = input;
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const data = await client.ask({
        question,
        project_id: repoId || 'default',
      });

      // Fetch git history and Jira issues in parallel
      const [gitRes, jiraRes] = await Promise.all([
        fetch(`/api/git/history?project_id=${repoId || 'default'}&limit=5`)
          .then(r => r.json())
          .catch(() => ({ commits: [] })),
        fetch(`/api/jira/issues?project_id=${repoId || 'default'}&limit=5`)
          .then(r => r.json())
          .catch(() => ({ issues: [] })),
      ]);

      const assistantMsg: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: data.answer || 'No response',
        claims: data.claims || [],
        status: data.status || 'success',
        suggestions: data.suggestions || [],
        disclaimer: '',
        source: 'spec_atlas',
        gitHistory: gitRes.commits || [],
        jiraIssues: jiraRes.issues || [],
        timestamp: Date.now(),
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      const errorMsg: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        status: 'error',
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderMessageContent = (msg: Message) => {
    const isExpanded = expandedMessage === msg.id;

    return (
      <div className="space-y-3 w-full">
        {/* Disclaimer (Deep Wiki fallback) */}
        {msg.disclaimer && (
          <div className="bg-yellow-900 bg-opacity-20 border border-yellow-700 border-opacity-50 rounded px-3 py-2 text-xs text-yellow-200">
            {msg.disclaimer}
          </div>
        )}

        {/* Main answer text */}
        <p className="text-sm leading-relaxed">{msg.content}</p>

        {/* Claims/Citations */}
        {msg.claims && msg.claims.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-600 space-y-2">
            <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide">Sources</p>
            <div className="flex flex-wrap gap-2">
              {msg.claims.map((claim, i) => (
                <CitationChip
                  key={i}
                  source={claim.source}
                  onClick={() => {
                    console.log('Clicked citation:', claim.source);
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* References Toggle & Panel */}
        {(msg.gitHistory?.length || 0 > 0 || msg.jiraIssues?.length || 0 > 0) && (
          <div className="mt-4 pt-3 border-t border-slate-600 space-y-3">
            <button
              onClick={() => setExpandedMessage(isExpanded ? null : msg.id)}
              className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 uppercase tracking-wide flex items-center gap-2"
            >
              <span>{isExpanded ? '▼' : '▶'}</span>
              Show References ({(msg.gitHistory?.length || 0) + (msg.jiraIssues?.length || 0)})
            </button>

            {isExpanded && (
              <div className="bg-slate-900 rounded border border-slate-700 p-3 space-y-3 text-xs">
                {/* Git History */}
                {msg.gitHistory && msg.gitHistory.length > 0 && (
                  <div>
                    <p className="font-semibold text-slate-300 mb-2">Recent Commits</p>
                    <div className="space-y-1">
                      {msg.gitHistory.map((commit, i) => (
                        <div key={i} className="bg-slate-800 rounded px-2 py-1.5">
                          <code className="text-cyan-400 text-xs">{commit.short_sha}</code>
                          <p className="text-slate-300 text-xs mt-0.5">{commit.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Jira Issues */}
                {msg.jiraIssues && msg.jiraIssues.length > 0 && (
                  <div>
                    <p className="font-semibold text-slate-300 mb-2">Related Issues</p>
                    <div className="space-y-1">
                      {msg.jiraIssues.map((issue, i) => (
                        <div key={i} className="bg-slate-800 rounded px-2 py-1.5">
                          <div className="flex items-center gap-2">
                            <code className="text-purple-400 text-xs font-bold">{issue.key}</code>
                            <span className={`text-xs px-1 rounded ${
                              issue.status === 'Done' ? 'bg-green-900 text-green-300' :
                              issue.status === 'In Progress' ? 'bg-blue-900 text-blue-300' :
                              'bg-slate-700 text-slate-300'
                            }`}>
                              {issue.status}
                            </span>
                          </div>
                          <p className="text-slate-300 text-xs mt-0.5">{issue.summary}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Suggestions for empty_db or no_results */}
        {msg.suggestions && msg.suggestions.length > 0 && msg.status !== 'success' && (
          <div className="mt-4 pt-3 border-t border-slate-600 space-y-2">
            <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide">Suggestions</p>
            <ul className="space-y-1">
              {msg.suggestions.map((suggestion, i) => (
                <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
                  <span className="text-cyan-400 mt-0.5 font-bold">•</span>
                  <span>{suggestion}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-b from-slate-900 to-slate-950">
      <TopBar variant="workspace" />

      {/* Subheader */}
      <div className="flex-shrink-0 border-b border-slate-700 bg-slate-950 px-6 py-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white">Ask About Your Code</h1>
          <p className="text-sm text-slate-400 mt-2">
            Repository: <code className="text-cyan-400">{repoId || 'default'}</code>
          </p>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full min-h-96 text-center">
              <h2 className="text-xl font-semibold text-white mb-2">What would you like to know?</h2>
              <p className="text-slate-400 mb-6 max-w-md">
                Ask questions about your code and get grounded answers with exact source citations.
              </p>
              <div className="text-left bg-slate-800 rounded-lg p-4 max-w-md">
                <p className="text-xs text-slate-400 uppercase font-semibold mb-3">Example questions:</p>
                <ul className="space-y-2 text-sm text-slate-300">
                  <li>• "What does the authentication module do?"</li>
                  <li>• "Where is the database connection defined?"</li>
                  <li>• "What are the main exports from this file?"</li>
                  <li>• "How does the API handle errors?"</li>
                </ul>
              </div>
            </div>
          )}

          {messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-2xl px-4 py-3 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-cyan-600 text-white rounded-br-none'
                    : `bg-slate-800 text-slate-100 rounded-bl-none ${
                        msg.status === 'empty_db' || msg.status === 'no_results'
                          ? 'border border-yellow-600 bg-slate-800'
                          : ''
                      } ${msg.status === 'error' ? 'border border-red-600 bg-slate-800' : ''}`
                }`}
              >
                {renderMessageContent(msg)}

                {/* Copy button for assistant messages */}
                {msg.role === 'assistant' && (
                  <button
                    onClick={() => copyToClipboard(msg.content, msg.id)}
                    className="mt-3 inline-flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200 transition"
                    title="Copy response"
                  >
                    {copiedId === msg.id ? (
                      <>
                        <Check size={14} /> Copied
                      </>
                    ) : (
                      <>
                        <Copy size={14} /> Copy
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 text-slate-100 px-4 py-3 rounded-lg rounded-bl-none">
                <div className="flex items-center gap-2">
                  <span className="inline-block w-2 h-2 bg-cyan-400 rounded-full animate-bounce" />
                  <span className="inline-block w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                  <span className="inline-block w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={scrollRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 border-t border-slate-700 bg-slate-950 px-4 py-4 sm:px-6">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSend} className="space-y-3">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask a question about your code..."
                disabled={isLoading}
                className="flex-1 bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 placeholder-slate-500 disabled:opacity-50"
                autoFocus
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-700 text-white px-4 py-3 rounded-lg font-semibold transition flex items-center gap-2"
              >
                <Send size={18} />
                <span className="hidden sm:inline">Send</span>
              </button>
            </div>
            <p className="text-xs text-slate-500">
              Press <kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">Enter</kbd> to send
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

export default RepoAsk;
