import React, { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  ClipboardCheck,
  Database,
  FileText,
  Play,
  Search,
  Send,
  ShieldCheck,
  Upload,
} from 'lucide-react';
import './styles.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8002/api';

type HealthState = 'checking' | 'ok' | 'failed';

type DocumentRecord = {
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  knowledge_base: string;
  status: string;
  created_at: string;
};

type DocumentChunk = {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  char_count: number;
  page_start: number | null;
  page_end: number | null;
  created_at: string;
};

type SearchResult = {
  document_id: string;
  chunk_id: string;
  chunk_index: number;
  score: number;
  combined_score: number;
  keyword_score: number;
  source_filename: string | null;
  content: string;
  page_start: number | null;
  page_end: number | null;
};

type QAResponse = {
  query: string;
  rewritten_query: string;
  answer: string;
  latency_ms: number;
  citations: SearchResult[];
};

type SearchLog = {
  id: string;
  query: string;
  rewritten_query: string;
  answer: string;
  hit_count: number;
  latency_ms: number;
  created_at: string;
};

type EvaluationCase = {
  id: string;
  question: string;
  expected_keywords: string;
  created_at: string;
};

type EvaluationRun = {
  id: string;
  case_id: string;
  answer: string;
  score: number;
  passed: boolean;
  created_at: string;
};

function App() {
  const [health, setHealth] = useState<HealthState>('checking');
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [answer, setAnswer] = useState<QAResponse | null>(null);
  const [logs, setLogs] = useState<SearchLog[]>([]);
  const [evaluationCases, setEvaluationCases] = useState<EvaluationCase[]>([]);
  const [evaluationRuns, setEvaluationRuns] = useState<EvaluationRun[]>([]);
  const [activeDocumentId, setActiveDocumentId] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [knowledgeBase, setKnowledgeBase] = useState('default');
  const [query, setQuery] = useState('人工智能安全治理框架包括哪些核心内容？');
  const [evalQuestion, setEvalQuestion] = useState('人工智能安全治理框架主要包括哪些核心内容？');
  const [evalKeywords, setEvalKeywords] = useState('治理,安全,风险,合规');
  const [uploading, setUploading] = useState(false);
  const [parsingId, setParsingId] = useState('');
  const [indexingId, setIndexingId] = useState('');
  const [searching, setSearching] = useState(false);
  const [answering, setAnswering] = useState(false);
  const [runningCaseId, setRunningCaseId] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchHealth();
    fetchDocuments();
    fetchLogs();
    fetchEvaluationCases();
    fetchEvaluationRuns();
  }, []);

  async function fetchHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      setHealth(response.ok ? 'ok' : 'failed');
    } catch {
      setHealth('failed');
    }
  }

  async function fetchDocuments() {
    const response = await fetch(`${API_BASE_URL}/documents`);
    if (response.ok) setDocuments(await response.json());
  }

  async function fetchLogs() {
    const response = await fetch(`${API_BASE_URL}/search/logs`);
    if (response.ok) setLogs(await response.json());
  }

  async function fetchEvaluationCases() {
    const response = await fetch(`${API_BASE_URL}/evaluations/cases`);
    if (response.ok) setEvaluationCases(await response.json());
  }

  async function fetchEvaluationRuns() {
    const response = await fetch(`${API_BASE_URL}/evaluations/runs`);
    if (response.ok) setEvaluationRuns(await response.json());
  }

  async function fetchChunks(documentId: string) {
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}/chunks`);
    if (response.ok) {
      setActiveDocumentId(documentId);
      setChunks(await response.json());
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
    setMessage('');
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setMessage('请先选择一个文档。');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('knowledge_base', knowledgeBase.trim() || 'default');
    setUploading(true);
    setMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error((await readError(response)) || '上传失败');
      setSelectedFile(null);
      setMessage('上传成功，文档元数据已保存。');
      await fetchDocuments();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '上传失败');
    } finally {
      setUploading(false);
    }
  }

  async function handleParse(document: DocumentRecord) {
    setParsingId(document.id);
    setMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/documents/${document.id}/parse`, {
        method: 'POST',
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || '解析失败');
      setMessage(`解析完成，共生成 ${result.chunk_count} 个知识片段。`);
      await fetchDocuments();
      await fetchChunks(document.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '解析失败');
      await fetchDocuments();
    } finally {
      setParsingId('');
    }
  }

  async function handleIndex(document: DocumentRecord) {
    setIndexingId(document.id);
    setMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/documents/${document.id}/index`, {
        method: 'POST',
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || '入库失败');
      setMessage(`向量入库完成，共写入 ${result.indexed_count} 个知识片段。`);
      await fetchDocuments();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '入库失败');
    } finally {
      setIndexingId('');
    }
  }

  async function handleRetrieve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) {
      setMessage('请输入检索问题。');
      return;
    }

    setSearching(true);
    setMessage('');
    try {
      const params = new URLSearchParams({ query, limit: '5' });
      if (knowledgeBase.trim() && knowledgeBase.trim() !== 'default') params.set('knowledge_base', knowledgeBase.trim());
      const response = await fetch(`${API_BASE_URL}/search?${params.toString()}`);
      const result = await response.json().catch(() => []);
      if (!response.ok) throw new Error(result.detail || '检索失败');
      setSearchResults(result);
      setMessage(`检索完成，召回 ${result.length} 个片段。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '检索失败');
    } finally {
      setSearching(false);
    }
  }

  async function handleAnswer() {
    if (!query.trim()) {
      setMessage('请输入问答问题。');
      return;
    }

    setAnswering(true);
    setMessage('');
    try {
      const params = new URLSearchParams({ query, limit: '5' });
      if (knowledgeBase.trim() && knowledgeBase.trim() !== 'default') params.set('knowledge_base', knowledgeBase.trim());
      const response = await fetch(`${API_BASE_URL}/search/answer?${params.toString()}`);
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || '生成回答失败');
      setAnswer(result);
      setSearchResults(result.citations ?? []);
      setMessage(`回答生成完成，耗时 ${result.latency_ms} ms。`);
      await fetchLogs();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '生成回答失败');
    } finally {
      setAnswering(false);
    }
  }

  async function handleCreateEvalCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const response = await fetch(`${API_BASE_URL}/evaluations/cases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: evalQuestion, expected_keywords: evalKeywords }),
      });
      if (!response.ok) throw new Error((await readError(response)) || '新增评测用例失败');
      setMessage('评测用例已新增。');
      await fetchEvaluationCases();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '新增评测用例失败');
    }
  }

  async function handleRunCase(caseId: string) {
    setRunningCaseId(caseId);
    try {
      const response = await fetch(`${API_BASE_URL}/evaluations/cases/${caseId}/run`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error((await readError(response)) || '运行评测失败');
      setMessage('评测运行完成。');
      await fetchEvaluationRuns();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '运行评测失败');
    } finally {
      setRunningCaseId('');
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>企业知识库 RAG 工作台</h1>
            <p>文档解析、向量检索、引用问答、检索日志和基础评测的一体化应用</p>
          </div>
          <span className={`status status-${health}`}>API {health === 'checking' ? '检查中' : health}</span>
        </header>

        <section className="metric-grid">
          <FeatureCard icon={<FileText />} title="文档处理" text="支持常见文档上传、解析和分块。" />
          <FeatureCard icon={<Database />} title="向量入库" text="知识片段写入 Qdrant，保留来源信息。" />
          <FeatureCard icon={<Search />} title="混合检索" text="向量召回后结合关键词相似度二次排序。" />
          <FeatureCard icon={<ShieldCheck />} title="引用溯源" text="回答展示文档名、页码和片段来源。" />
        </section>

        <section className="panel-grid">
          <section className="panel">
            <h2>文档上传</h2>
            <form onSubmit={handleUpload} className="upload-form">
              <label>
                知识库
                <input
                  className="text-input"
                  value={knowledgeBase}
                  onChange={(event) => setKnowledgeBase(event.target.value)}
                />
              </label>
              <label className="file-picker">
                <Upload />
                <span>{selectedFile ? selectedFile.name : '选择 PDF / TXT / Markdown / DOCX'}</span>
                <input type="file" accept=".pdf,.txt,.md,.docx" onChange={handleFileChange} />
              </label>
              <button type="submit" disabled={uploading}>
                {uploading ? '上传中...' : '上传文档'}
              </button>
            </form>
            {message && <p className="message">{message}</p>}
          </section>

          <section className="panel">
            <h2>文档列表</h2>
            <div className="document-list">
              {documents.length === 0 ? (
                <p className="empty-text">还没有上传文档。</p>
              ) : (
                documents.map((document) => (
                  <article className="document-row" key={document.id}>
                    <div>
                      <strong>{document.original_filename}</strong>
                      <p>
                        {document.knowledge_base} / {formatBytes(document.size_bytes)} / {document.content_type}
                      </p>
                    </div>
                    <div className="document-actions">
                      <span>{document.status}</span>
                      <button
                        type="button"
                        className="icon-button"
                        onClick={() => handleParse(document)}
                        disabled={parsingId === document.id}
                        title="解析文档"
                      >
                        <Play />
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => handleIndex(document)}
                        disabled={indexingId === document.id}
                      >
                        入库
                      </button>
                      <button type="button" className="secondary-button" onClick={() => fetchChunks(document.id)}>
                        查看分块
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </section>

        <section className="panel search-panel">
          <h2>知识库问答</h2>
          <form className="search-form" onSubmit={handleRetrieve}>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入企业知识库问题" />
            <button type="submit" disabled={searching}>
              <Search />
              {searching ? '检索中...' : '召回'}
            </button>
            <button type="button" disabled={answering} onClick={handleAnswer}>
              <Send />
              {answering ? '生成中...' : '回答'}
            </button>
          </form>

          {answer && (
            <article className="answer-box">
              <div className="answer-meta">
                <strong>带引用回答</strong>
                <span>改写查询：{answer.rewritten_query}</span>
                <span>{answer.latency_ms} ms</span>
              </div>
              <pre>{answer.answer}</pre>
            </article>
          )}

          <div className="search-results">
            {searchResults.map((result, index) => (
              <article className="chunk-row" key={result.chunk_id}>
                <div className="chunk-meta">
                  <strong>引用 [{index + 1}]</strong>
                  <span>综合 {score(result.combined_score)}</span>
                  <span>向量 {score(result.score)}</span>
                  <span>关键词 {score(result.keyword_score)}</span>
                  {result.source_filename && <span>{result.source_filename}</span>}
                  {result.page_start && <span>第 {result.page_start} 页</span>}
                </div>
                <p>{result.content}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="panel-grid bottom-grid">
          <section className="panel chunk-panel">
            <h2>分块预览</h2>
            {chunks.length === 0 ? (
              <p className="empty-text">解析文档后，这里会展示可用于检索的知识片段。</p>
            ) : (
              <div className="chunk-list">
                {chunks.slice(0, 5).map((chunk) => (
                  <article className="chunk-row" key={chunk.id}>
                    <div className="chunk-meta">
                      <strong>#{chunk.chunk_index + 1}</strong>
                      <span>{chunk.char_count} 字符</span>
                      {chunk.page_start && <span>第 {chunk.page_start} 页</span>}
                    </div>
                    <p>{chunk.content}</p>
                  </article>
                ))}
              </div>
            )}
            {activeDocumentId && chunks.length > 5 && <p className="chunk-note">当前仅预览前 5 个片段，共 {chunks.length} 个。</p>}
          </section>

          <section className="panel">
            <h2>日志与评测</h2>
            <div className="mini-section">
              <h3>
                <ClipboardCheck />
                评测用例
              </h3>
              <form className="eval-form" onSubmit={handleCreateEvalCase}>
                <input value={evalQuestion} onChange={(event) => setEvalQuestion(event.target.value)} />
                <input value={evalKeywords} onChange={(event) => setEvalKeywords(event.target.value)} />
                <button type="submit">新增</button>
              </form>
              <div className="small-list">
                {evaluationCases.slice(0, 4).map((item) => (
                  <article key={item.id}>
                    <strong>{item.question}</strong>
                    <span>期望：{item.expected_keywords}</span>
                    <button type="button" onClick={() => handleRunCase(item.id)} disabled={runningCaseId === item.id}>
                      运行
                    </button>
                  </article>
                ))}
              </div>
            </div>

            <div className="mini-section">
              <h3>
                <Activity />
                最近结果
              </h3>
              <div className="small-list">
                {evaluationRuns.slice(0, 3).map((item) => (
                  <article key={item.id}>
                    <strong>{item.passed ? '通过' : '未通过'} / {Math.round(item.score * 100)}%</strong>
                    <span>{item.answer}</span>
                  </article>
                ))}
                {logs.slice(0, 3).map((item) => (
                  <article key={item.id}>
                    <strong>{item.query}</strong>
                    <span>命中 {item.hit_count} 个片段 / {item.latency_ms} ms</span>
                  </article>
                ))}
              </div>
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}

function FeatureCard({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <article className="feature-card">
      <div className="icon-wrap">{icon}</div>
      <h2>{title}</h2>
      <p>{text}</p>
    </article>
  );
}

async function readError(response: Response) {
  const error = await response.json().catch(() => ({}));
  return typeof error.detail === 'string' ? error.detail : '';
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function score(value: number) {
  return Number.isFinite(value) ? value.toFixed(3) : '0.000';
}

createRoot(document.getElementById('root')!).render(<App />);
