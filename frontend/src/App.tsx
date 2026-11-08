import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  BookOpenText,
  Check,
  ChevronDown,
  CircleHelp,
  CloudUpload,
  FileText,
  Layers3,
  // Menu,
  MessageSquarePlus,
  Paperclip,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  ScanSearch,
  Sparkles,
  X,
  Zap,
} from "lucide-react";
import { ask, checkHealth, uploadDocument, type Source } from "./api";

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  usedRag?: boolean;
  error?: boolean;
};
type UploadedDoc = { name: string; chunks: number; id: string };
const suggestions = [
  {
    icon: BookOpenText,
    title: "Summarize a document",
    detail: "Get the key insights from your uploaded files",
    question: "Summarize the main points in my uploaded document.",
  },
  {
    icon: ScanSearch,
    title: "Find specific information",
    detail: "Ask precise questions about your sources",
    question: "What are the most important details in the document?",
  },
  {
    icon: Zap,
    title: "Explore an idea",
    detail: "Use ClarityLM for a quick explanation",
    question: "Explain how retrieval-augmented generation works.",
  },
];
let messageId = 1;

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="brand">
      <div className="brand-symbol">
        <Layers3 size={20} strokeWidth={2.5} />
      </div>
      {!compact && (
        <span>
          Clarity<span className="brand-accent">LM</span>
        </span>
      )}
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [useRag, setUseRag] = useState(true);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [documents, setDocuments] = useState<UploadedDoc[]>([]);
  const [status, setStatus] = useState<"checking" | "online" | "offline">(
    "checking",
  );
  const [notification, setNotification] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [expandedSources, setExpandedSources] = useState<
    Record<number, boolean>
  >({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    void checkHealth().then((online) =>
      setStatus(online ? "online" : "offline"),
    );
  }, []);
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);

  const submit = async (text = question) => {
    const input = text.trim();
    if (!input || busy || uploading) return;
    const mode = useRag;
    setQuestion("");
    setNotification(null);
    setMessages((items) => [
      ...items,
      { id: messageId++, role: "user", content: input },
    ]);
    setBusy(true);
    try {
      const result = await ask(input, mode);
      setMessages((items) => [
        ...items,
        {
          id: messageId++,
          role: "assistant",
          content: result.answer || "(No answer returned)",
          sources: result.sources ?? [],
          usedRag: mode,
        },
      ]);
      setStatus("online");
    } catch (error) {
      const detail =
        error instanceof Error ? error.message : "Could not reach the server.";
      setMessages((items) => [
        ...items,
        { id: messageId++, role: "assistant", content: detail, error: true },
      ]);
      setStatus("offline");
    } finally {
      setBusy(false);
    }
  };

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!files.length || uploading) return;
    setNotification(null);
    setUploading(true);
    let successes = 0;
    for (const file of files) {
      if (!/\.(pdf|txt|md)$/i.test(file.name)) {
        setNotification(
          `${file.name}: only PDF, TXT and MD files are supported.`,
        );
        continue;
      }
      if (file.size > 5 * 1024 * 1024) {
        setNotification(`${file.name}: files must be 5 MB or smaller.`);
        continue;
      }
      try {
        const result = await uploadDocument(file);
        setDocuments((current) => [
          ...current.filter((doc) => doc.name !== result.filename),
          {
            name: result.filename,
            chunks: result.chunks,
            id: result.document_id,
          },
        ]);
        successes++;
        setStatus("online");
      } catch (error) {
        setNotification(
          `${file.name}: ${error instanceof Error ? error.message : "Upload failed."}`,
        );
      }
    }
    if (successes)
      setNotification(
        `${successes} document${successes === 1 ? "" : "s"} indexed successfully. RAG is ready.`,
      );
    setUploading(false);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  };
  const resetChat = () => {
    setMessages([]);
    setExpandedSources({});
    setQuestion("");
    setNotification(null);
  };

  return (
    <div className="app-layout">
      {sidebarOpen && (
        <aside className="sidebar">
          <div className="sidebar-top">
            <Brand />
            <button
              className="icon-button sidebar-close"
              onClick={() => setSidebarOpen(false)}
              title="Hide sidebar"
            >
              <PanelLeftClose size={19} />
            </button>
          </div>
          <button className="new-chat" onClick={resetChat}>
            <MessageSquarePlus size={17} /> New conversation{" "}
            <Plus size={17} className="ml-auto" />
          </button>
          <div className="sidebar-section">
            <div className="sidebar-heading">
              <span>KNOWLEDGE BASE</span>
              <span className="count-chip">{documents.length}</span>
            </div>
            <button
              className="upload-box"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              <CloudUpload size={22} />
              <strong>
                {uploading ? "Indexing document…" : "Upload documents"}
              </strong>
              <span>PDF, TXT or Markdown · Max 5 MB</span>
            </button>
            <input
              ref={fileInputRef}
              className="hidden"
              type="file"
              accept=".pdf,.txt,.md"
              multiple
              onChange={(event) => void upload(event)}
            />
            <div className="document-list">
              {documents.map((doc) => (
                <div className="document-row" key={doc.id} title={doc.name}>
                  <div className="document-icon">
                    <FileText size={17} />
                  </div>
                  <div className="document-details">
                    <div>{doc.name}</div>
                    <span>{doc.chunks} chunks indexed</span>
                  </div>
                  <Check size={15} className="text-emerald-600" />
                </div>
              ))}
            </div>
            {documents.length === 0 && (
              <div className="empty-document-hint">
                Your uploaded documents will appear here.
              </div>
            )}
          </div>
          <div className="sidebar-bottom">
            <div className="sidebar-info">
              <CircleHelp size={16} />
              <span>Built with TinyLlama, FastAPI & Qdrant</span>
            </div>
            <div className="sidebar-footer">
              ClarityLM <span>·</span> Portfolio project
            </div>
          </div>
        </aside>
      )}
      <main className="main">
        <header className="topbar">
          <div className="topbar-left">
            {!sidebarOpen && (
              <button
                className="icon-button"
                onClick={() => setSidebarOpen(true)}
                title="Show sidebar"
              >
                <PanelLeftOpen size={20} />
              </button>
            )}
            <div className="topbar-title">
              ClarityLM <ChevronDown size={15} />
            </div>
            <span className="topbar-beta">RAG WORKSPACE</span>
          </div>
          <div className="topbar-right">
            <span className={`status-dot ${status}`} />
            <span className="status-label">
              {status === "online"
                ? "API connected"
                : status === "checking"
                  ? "Checking API"
                  : "API offline"}
            </span>
            <span className="header-separator" />
            <span className="model-label">
              <Sparkles size={15} /> TinyLlama 1.1B
            </span>
          </div>
        </header>
        <div className="chat-scroll" ref={scrollRef}>
          {messages.length === 0 ? (
            <section className="welcome">
              <div className="welcome-mark">
                <Layers3 size={29} strokeWidth={2.2} />
              </div>
              <div className="welcome-eyebrow">YOUR AI RESEARCH ASSISTANT</div>
              <h1>
                Good questions lead to
                <br />
                <span>clearer answers.</span>
              </h1>
              <p>
                Meet ClarityLM, your intelligent workspace for understanding
                documents and exploring ideas. Ask anything to get started.
              </p>
              <div className="suggestion-grid">
                {suggestions.map((s) => (
                  <button
                    className="suggestion"
                    key={s.title}
                    onClick={() => void submit(s.question)}
                    disabled={busy}
                  >
                    <div className="suggestion-icon">
                      <s.icon size={18} />
                    </div>
                    <strong>{s.title}</strong>
                    <span>{s.detail}</span>
                    <ArrowRight className="suggestion-arrow" size={16} />
                  </button>
                ))}
              </div>
              <div className="welcome-tip">
                <Sparkles size={15} /> Upload a document to unlock
                source-grounded answers with RAG.
              </div>
            </section>
          ) : (
            <div className="thread">
              {messages.map((message) => (
                <div className={`message ${message.role}`} key={message.id}>
                  <div className={`avatar ${message.role}`}>
                    {message.role === "assistant" ? (
                      <Layers3 size={17} />
                    ) : (
                      "You"
                    )}
                  </div>
                  <div className="message-body">
                    <div className="message-author">
                      {message.role === "assistant" ? "ClarityLM" : "You"}
                      {message.role === "assistant" && !message.error && (
                        <span className="message-mode">
                          {message.usedRag ? "RAG enabled" : "Model only"}
                        </span>
                      )}
                    </div>
                    <div
                      className={`message-text ${message.error ? "error-text" : ""}`}
                    >
                      {message.content}
                    </div>
                    {!!message.sources?.length && (
                      <div className="sources">
                        <button
                          className="sources-toggle"
                          onClick={() =>
                            setExpandedSources((s) => ({
                              ...s,
                              [message.id]: !s[message.id],
                            }))
                          }
                        >
                          <BookOpenText size={15} /> {message.sources.length}{" "}
                          source{message.sources.length === 1 ? "" : "s"} used{" "}
                          <ChevronDown
                            size={14}
                            className={
                              expandedSources[message.id] ? "rotate" : ""
                            }
                          />
                        </button>
                        {expandedSources[message.id] && (
                          <div className="source-list">
                            {message.sources.map((source, idx) => (
                              <div className="source-item" key={source.id}>
                                <div className="source-title">
                                  <FileText size={15} />
                                  <strong>
                                    {String(
                                      source.metadata?.path ??
                                        `Source ${idx + 1}`,
                                    )
                                      .split("/")
                                      .pop()}
                                  </strong>
                                  <span>
                                    {Math.round(source.score * 100)}% match
                                  </span>
                                </div>
                                <div className="source-text">{source.text}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {busy && (
                <div className="message assistant">
                  <div className="avatar assistant">
                    <Layers3 size={17} />
                  </div>
                  <div className="message-body">
                    <div className="message-author">ClarityLM</div>
                    <div className="typing">
                      <span />
                      <span />
                      <span />
                    </div>
                    <div className="thinking-label">Generating response…</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        <div className="composer-area">
          {notification && (
            <div className="notice">
              <span>{notification}</span>
              <button onClick={() => setNotification(null)} title="Dismiss">
                <X size={16} />
              </button>
            </div>
          )}
          {messages.length > 0 && (
            <button
              className="scroll-bottom"
              onClick={() =>
                scrollRef.current?.scrollTo({
                  top: scrollRef.current.scrollHeight,
                  behavior: "smooth",
                })
              }
            >
              <ArrowDown size={14} /> Latest
            </button>
          )}
          <div className="composer">
            <textarea
              ref={textareaRef}
              rows={2}
              placeholder="Ask ClarityLM anything…"
              aria-label="Ask ClarityLM"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={busy}
            />
            <div className="composer-actions">
              <div className="composer-left">
                <button
                  className="attach-button"
                  title="Upload a document"
                  disabled={uploading}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Paperclip size={18} />
                </button>
                <span className="composer-divider" />
                <button
                  className={`rag-switch ${useRag ? "active" : ""}`}
                  onClick={() => setUseRag(!useRag)}
                  aria-pressed={useRag}
                >
                  <span className="toggle-track">
                    <span />
                  </span>
                  <ScanSearch size={15} /> RAG {useRag ? "On" : "Off"}
                </button>
              </div>
              <button
                className="send-button"
                onClick={() => void submit()}
                disabled={!question.trim() || busy || uploading}
                aria-label="Send message"
              >
                <ArrowUp size={19} strokeWidth={2.5} />
              </button>
            </div>
          </div>
          <p className="composer-footnote">
            ClarityLM can make mistakes. Verify important information against
            original sources.
          </p>
        </div>
      </main>
    </div>
  );
}
