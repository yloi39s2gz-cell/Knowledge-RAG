import React, { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Database, FileText, Play, Search, Send, ShieldCheck, Upload } from 'lucide-react';
import './styles.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001/api';

type HealthState = 'checking' | 'ok' | 'failed';

type DocumentRecord = {
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
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
  content: string;
  page_start: number | null;
  page_end: number | null;
};

function App() {
  const [health, setHealth] = useState<HealthState>('checking');
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [activeDocumentId, setActiveDocumentId] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [query, setQuery] = useState('人工智能安全治理框架包括哪些核心内容？');
  const [uploading, setUploading] = useState(false);
  const [parsingId, setParsingId] = useState('');
  const [indexingId, setIndexingId] = useState('');
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchHealth();
    fetchDocuments();
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
    if (response.ok) {
      setDocuments(await response.json());
    }
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
    setUploading(true);
    setMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || '上传失败');
      }
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
      if (!response.ok) {
        throw new Error(result.detail || '解析失败');
      }
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
      if (!response.ok) {
        throw new Error(result.detail || '入库失败');
      }
      setMessage(`向量入库完成，共写入 ${result.indexed_count} 个知识片段。`);
      await fetchDocuments();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '入库失败');
    } finally {
      setIndexingId('');
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) {
      setMessage('请输入检索问题。');
      return;
    }

    setSearching(true);
    setMessage('');
    try {
      const params = new URLSearchParams({ query, limit: '5' });
      const response = await fetch(`${API_BASE_URL}/search?${params.toString()}`);
      const result = await response.json().catch(() => []);
      if (!response.ok) {
        throw new Error(result.detail || '检索失败');
      }
      setSearchResults(result);
      setMessage(`检索完成，召回 ${result.length} 个片段。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '检索失败');
    } finally {
      setSearching(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>Enterprise Knowledge RAG</h1>
            <p>面向企业知识库场景的可部署 RAG 应用</p>
          </div>
          <span className={`status status-${health}`}>
            API {health === 'checking' ? 'checking' : health}
          </span>
        </header>

        <section className="metric-grid">
          <FeatureCard
            icon={<FileText />}
            title="文档处理"
            text="上传 PDF、TXT、Markdown、DOCX，解析文本并生成知识片段。"
          />
          <FeatureCard
            icon={<Database />}
            title="向量入库"
            text="将 chunk 转成向量并写入 Qdrant，建立可检索索引。"
          />
          <FeatureCard
            icon={<Search />}
            title="向量检索"
            text="根据问题向量召回相关片段，为问答提供上下文。"
          />
          <FeatureCard
            icon={<ShieldCheck />}
            title="引用溯源"
            text="保留 chunk、页码和来源信息，方便审计与核查。"
          />
        </section>

        <section className="panel-grid">
          <section className="panel">
            <h2>文档上传</h2>
            <p>当前模块会保存原始文件和元数据，解析后进入 embedding 与检索链路。</p>
            <form onSubmit={handleUpload} className="upload-form">
              <label className="file-picker">
                <Upload />
                <span>{selectedFile ? selectedFile.name : '选择 PDF / TXT / Markdown / DOCX'}</span>
                <input
                  type="file"
                  accept=".pdf,.txt,.md,.docx"
                  onChange={handleFileChange}
                />
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
                        {formatBytes(document.size_bytes)} / {document.content_type}
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
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => fetchChunks(document.id)}
                      >
                        查看 chunks
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </section>

        <section className="panel search-panel">
          <h2>向量检索测试</h2>
          <form className="search-form" onSubmit={handleSearch}>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="输入一个企业知识库问题"
            />
            <button type="submit" disabled={searching}>
              <Send />
              {searching ? '检索中...' : '检索'}
            </button>
          </form>
          <div className="search-results">
            {searchResults.map((result) => (
              <article className="chunk-row" key={result.chunk_id}>
                <div className="chunk-meta">
                  <strong>score {result.score.toFixed(3)}</strong>
                  <span>chunk #{result.chunk_index + 1}</span>
                  {result.page_start && <span>page {result.page_start}</span>}
                </div>
                <p>{result.content}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="panel chunk-panel">
          <h2>Chunk 预览</h2>
          {chunks.length === 0 ? (
            <p className="empty-text">解析文档后，这里会展示可用于检索的知识片段。</p>
          ) : (
            <div className="chunk-list">
              {chunks.slice(0, 6).map((chunk) => (
                <article className="chunk-row" key={chunk.id}>
                  <div className="chunk-meta">
                    <strong>#{chunk.chunk_index + 1}</strong>
                    <span>{chunk.char_count} chars</span>
                    {chunk.page_start && <span>page {chunk.page_start}</span>}
                  </div>
                  <p>{chunk.content}</p>
                </article>
              ))}
            </div>
          )}
          {activeDocumentId && chunks.length > 6 && (
            <p className="chunk-note">当前仅预览前 6 个片段，共 {chunks.length} 个。</p>
          )}
        </section>

        <section className="roadmap">
          <h2>第一阶段目标</h2>
          <ol>
            <li>跑通前后端工程骨架</li>
            <li>实现文档上传与文件元数据保存</li>
            <li>完成 PDF 解析与 chunk 分块</li>
            <li>接入 embedding 与 Qdrant 向量数据库</li>
          </ol>
        </section>
      </section>
    </main>
  );
}

function FeatureCard({
  icon,
  title,
  text,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
}) {
  return (
    <article className="feature-card">
      <div className="icon-wrap">{icon}</div>
      <h2>{title}</h2>
      <p>{text}</p>
    </article>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

createRoot(document.getElementById('root')!).render(<App />);
