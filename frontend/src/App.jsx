import React, { useState, useEffect } from 'react';

const DISCLAIMER = "La similarité faciale n'est pas une preuve d'identité. Vérifiez les sources avant toute conclusion.";

export default function App() {
  const [activeTab, setActiveTab] = useState('search');
  const [stats, setStats] = useState(null);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/scrape/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.log('API connect issue:', e);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#090d16' }}>
      {/* Header Banner */}
      <header className="glass-panel" style={{ padding: '1rem 2rem', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'linear-gradient(135deg, #38bdf8, #818cf8)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '1.2rem', color: '#090d16' }}>
              FL
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: '700', letterSpacing: '-0.02em', background: 'linear-gradient(to right, #f8fafc, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                FaceLens <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.5rem', borderRadius: '12px', background: 'rgba(56,189,248,0.15)', color: '#38bdf8', fontWeight: '600', marginLeft: '0.5rem' }}>Local & Self-Hosted</span>
              </h1>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#64748b' }}>Moteur de recherche biométrique & scraping intelligent</p>
            </div>
          </div>

          {stats && (
            <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem' }}>
              <div style={{ padding: '0.4rem 0.8rem', borderRadius: '8px', background: 'rgba(30,41,59,0.8)', border: '1px solid rgba(255,255,255,0.05)' }}>
                Vecteurs FAISS : <strong style={{ color: '#38bdf8' }}>{stats.faiss_ntotal}</strong>
              </div>
              <div style={{ padding: '0.4rem 0.8rem', borderRadius: '8px', background: 'rgba(30,41,59,0.8)', border: '1px solid rgba(255,255,255,0.05)' }}>
                Intégrité SQLite: <strong style={{ color: stats.integrity_verified ? '#34d399' : '#f87171' }}>{stats.integrity_verified ? 'OK' : 'ERREUR'}</strong>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Mandatory Biometric Disclaimer Notice */}
      <div style={{ background: 'rgba(245, 158, 11, 0.1)', borderBottom: '1px solid rgba(245, 158, 11, 0.2)', padding: '0.6rem 1rem', textAlign: 'center', fontSize: '0.85rem', color: '#fbbf24', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
        <span>⚠️</span>
        <span><strong>Avertissement Légal :</strong> {DISCLAIMER}</span>
      </div>

      {/* Main Container */}
      <main style={{ maxWidth: '1200px', width: '100%', margin: '2rem auto', padding: '0 1rem', flex: 1 }}>
        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', gap: '0.5rem', marginBottom: '2rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>
          {[
            { id: 'search', label: '🔍 Recherche 1:N' },
            { id: 'verify', label: '⚖️ Vérification 1:1' },
            { id: 'corpus', label: '📸 Corpus & Inscription' },
            { id: 'spider', label: '🕷️ Module Scraping' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '0.6rem 1.2rem',
                borderRadius: '8px',
                border: 'none',
                background: activeTab === tab.id ? '#38bdf8' : 'transparent',
                color: activeTab === tab.id ? '#090d16' : '#94a3b8',
                fontWeight: activeTab === tab.id ? '700' : '500',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Tab Components */}
        {activeTab === 'search' && <SearchTab />}
        {activeTab === 'verify' && <VerifyTab />}
        {activeTab === 'corpus' && <CorpusTab onRefreshStats={fetchStats} />}
        {activeTab === 'spider' && <SpiderTab onRefreshStats={fetchStats} />}
      </main>
    </div>
  );
}

// ---------------- TAB COMPONENTS ---------------- //

function SearchTab() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [minSim, setMinSim] = useState(0.0);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setResults(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`/api/faces/search?top_k=15&min_similarity=${minSim}`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        setResults(data);
      }
    } catch (err) {
      alert("Erreur de recherche : " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '2rem', borderRadius: '16px' }}>
      <h2 style={{ marginTop: 0 }}>Recherche par Visage (1:N)</h2>
      <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Uploadez la photo d'un visage pour trouver toutes les correspondances biométriques dans le corpus indexé.</p>

      <form onSubmit={handleSearch} style={{ margin: '1.5rem 0', display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ flex: 1, minWidth: '250px' }}>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const f = e.target.files[0];
              setFile(f);
              if (f) setPreview(URL.createObjectURL(f));
            }}
            style={{ display: 'none' }}
            id="search-file"
          />
          <label htmlFor="search-file" style={{ display: 'block', padding: '1rem', border: '2px dashed rgba(56,189,248,0.3)', borderRadius: '12px', textAlign: 'center', cursor: 'pointer', background: 'rgba(30,41,59,0.4)' }}>
            {preview ? (
              <img src={preview} alt="Query Preview" style={{ maxHeight: '140px', borderRadius: '8px', objectFit: 'cover' }} />
            ) : (
              <div style={{ color: '#94a3b8' }}>📁 Cliquez pour charger une image suspecte</div>
            )}
          </label>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', minWidth: '200px' }}>
          <label style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Seuil minimum : {(minSim * 100).toFixed(0)}%</label>
          <input type="range" min="0" max="0.9" step="0.05" value={minSim} onChange={(e) => setMinSim(parseFloat(e.target.value))} />
          <button type="submit" disabled={!file || loading} style={{ padding: '0.8rem 1.5rem', borderRadius: '8px', border: 'none', background: loading ? '#475569' : '#38bdf8', color: '#090d16', fontWeight: 'bold', cursor: 'pointer', marginTop: '0.5rem' }}>
            {loading ? 'Recherche en cours...' : 'Lancer la Recherche'}
          </button>
        </div>
      </form>

      {results && (
        <div style={{ marginTop: '2rem' }}>
          <h3>Résultats ({results.results.length} trouvé(s))</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '1.2rem', marginTop: '1rem' }}>
            {results.results.map(r => (
              <div key={r.id} className="glass-card" style={{ padding: '1rem', borderRadius: '12px' }}>
                <img src={r.image_path.replace(/.*data\/images/, '/static/images')} alt="Result" style={{ width: '100%', height: '180px', objectFit: 'cover', borderRadius: '8px' }} />
                <div style={{ marginTop: '0.8rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className={`badge-${r.verdict}`} style={{ padding: '0.2rem 0.6rem', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 'bold', textTransform: 'uppercase' }}>
                      {r.verdict}
                    </span>
                    <span style={{ fontSize: '1rem', fontWeight: 'bold', color: '#38bdf8' }}>{(r.similarity * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#f1f5f9', fontWeight: '600', marginTop: '0.4rem' }}>{r.person_name || 'Inconnu'}</div>
                  {r.source_url && (
                    <a href={r.source_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.75rem', color: '#38bdf8', textDecoration: 'none', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: '0.2rem' }}>
                      🔗 {r.source_url}
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function VerifyTab() {
  const [fileA, setFileA] = useState(null);
  const [fileB, setFileB] = useState(null);
  const [prevA, setPrevA] = useState(null);
  const [prevB, setPrevB] = useState(null);
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!fileA || !fileB) return;
    setLoading(true);
    setRes(null);

    const formData = new FormData();
    formData.append('image_a', fileA);
    formData.append('image_b', fileB);

    try {
      const response = await fetch('/api/faces/verify', {
        method: 'POST',
        body: formData
      });
      if (response.ok) {
        const data = await response.json();
        setRes(data);
      }
    } catch (err) {
      alert("Erreur de vérification : " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '2rem', borderRadius: '16px' }}>
      <h2>Vérification 1:1 de Deux Visages</h2>
      <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Comparez directement deux photos pour mesurer la distance biométrique exacte et déterminer s'il s'agit de la même personne.</p>

      <form onSubmit={handleVerify} style={{ margin: '1.5rem 0' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold', fontSize: '0.9rem' }}>Image A (Suspecte)</label>
            <input type="file" accept="image/*" onChange={(e) => { const f = e.target.files[0]; setFileA(f); if (f) setPrevA(URL.createObjectURL(f)); }} />
            {prevA && <img src={prevA} alt="A" style={{ width: '100%', maxHeight: '200px', objectFit: 'cover', borderRadius: '8px', marginTop: '0.5rem' }} />}
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold', fontSize: '0.9rem' }}>Image B (Candidat)</label>
            <input type="file" accept="image/*" onChange={(e) => { const f = e.target.files[0]; setFileB(f); if (f) setPrevB(URL.createObjectURL(f)); }} />
            {prevB && <img src={prevB} alt="B" style={{ width: '100%', maxHeight: '200px', objectFit: 'cover', borderRadius: '8px', marginTop: '0.5rem' }} />}
          </div>
        </div>

        <button type="submit" disabled={!fileA || !fileB || loading} style={{ marginTop: '1.5rem', padding: '0.8rem 2rem', width: '100%', borderRadius: '8px', border: 'none', background: loading ? '#475569' : '#38bdf8', color: '#090d16', fontWeight: 'bold', cursor: 'pointer' }}>
          {loading ? 'Analyse biométrique...' : 'Lancer la Vérification 1:1'}
        </button>
      </form>

      {res && (
        <div className="glass-card" style={{ padding: '1.5rem', borderRadius: '12px', textAlign: 'center', marginTop: '1.5rem' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: res.verified ? '#34d399' : '#f87171' }}>
            {res.verified ? 'VERIFIED (MÊME VISAGE)' : 'NON MATCH'}
          </div>
          <div style={{ fontSize: '1.2rem', marginTop: '0.5rem', color: '#38bdf8' }}>
            Similarité: <strong>{(res.similarity * 100).toFixed(1)}%</strong> | Distance: {res.distance}
          </div>
          <div style={{ marginTop: '0.5rem', color: '#94a3b8', fontSize: '0.9rem' }}>Verdict : {res.verdict.toUpperCase()} (Seuil utilisé : {res.threshold})</div>
          {res.warning && <div style={{ color: '#fbbf24', marginTop: '0.5rem', fontSize: '0.85rem' }}>⚠️ {res.warning}</div>}
        </div>
      )}
    </div>
  );
}

function CorpusTab({ onRefreshStats }) {
  const [file, setFile] = useState(null);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const handleEnroll = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);
    if (name) formData.append('person_name', name);
    if (url) formData.append('source_url', url);

    try {
      const res = await fetch('/api/faces/enroll', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        alert("Visage inscrit dans le corpus avec succès !");
        setFile(null);
        setName('');
        setUrl('');
        if (onRefreshStats) onRefreshStats();
      } else {
        const err = await res.json();
        alert("Erreur d'inscription : " + err.detail);
      }
    } catch (e) {
      alert("Erreur réseau : " + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '2rem', borderRadius: '16px' }}>
      <h2>Inscription Manuelle dans le Corpus</h2>
      <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Ajoutez un nouveau visage et ses métadonnées dans l'index FAISS et la base SQLite locale.</p>

      <form onSubmit={handleEnroll} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '500px', marginTop: '1.5rem' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.3rem' }}>Photo du Visage</label>
          <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0])} required />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.3rem' }}>Nom / Identité (Optionnel)</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex: John Doe" style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', background: '#1e293b', color: '#fff' }} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.3rem' }}>URL Source (Optionnel)</label>
          <input type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', background: '#1e293b', color: '#fff' }} />
        </div>

        <button type="submit" disabled={loading} style={{ padding: '0.8rem', borderRadius: '8px', border: 'none', background: '#38bdf8', color: '#090d16', fontWeight: 'bold', cursor: 'pointer', marginTop: '0.5rem' }}>
          {loading ? 'Inscription...' : 'Enregistrer au Corpus'}
        </button>
      </form>
    </div>
  );
}

function SpiderTab({ onRefreshStats }) {
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [query, setQuery] = useState('');
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [domainToExclude, setDomainToExclude] = useState('');

  const handleStartUrl = async (e) => {
    e.preventDefault();
    if (!scrapeUrl) return;

    try {
      const res = await fetch('/api/scrape/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: scrapeUrl, max_images: 30 })
      });
      if (res.ok) {
        const data = await res.json();
        setJobId(data.job_id);
      }
    } catch (e) {
      alert("Erreur de lancement : " + e.message);
    }
  };

  const handleStartSearch = async (e) => {
    e.preventDefault();
    if (!query) return;

    try {
      const res = await fetch('/api/scrape/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, limit: 20 })
      });
      if (res.ok) {
        const data = await res.json();
        setJobId(data.job_id);
      }
    } catch (e) {
      alert("Erreur de recherche SearXNG : " + e.message);
    }
  };

  const handleExcludeDomain = async (e) => {
    e.preventDefault();
    if (!domainToExclude) return;

    try {
      const res = await fetch(`/api/scrape/source/${encodeURIComponent(domainToExclude)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        const data = await res.json();
        alert(data.message);
        setDomainToExclude('');
        if (onRefreshStats) onRefreshStats();
      }
    } catch (e) {
      alert("Erreur d'exclusion : " + e.message);
    }
  };

  useEffect(() => {
    if (!jobId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/scrape/status/${jobId}`);
        if (res.ok) {
          const data = await res.json();
          setJobStatus(data);
          if (data.status === 'completed' || data.status === 'failed' || data.status === 'partial') {
            clearInterval(interval);
            if (onRefreshStats) onRefreshStats();
          }
        }
      } catch (e) {
        console.log(e);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [jobId]);

  return (
    <div className="glass-panel" style={{ padding: '2rem', borderRadius: '16px' }}>
      <h2>Module Scraping "Spider"</h2>
      <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Collectez automatiquement les visages des pages publiques et enrichissez le corpus avec déduplication 0.95.</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '1.5rem' }}>
        <div className="glass-card" style={{ padding: '1.2rem', borderRadius: '12px' }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1rem' }}>Scraper une URL Publique</h3>
          <form onSubmit={handleStartUrl}>
            <input type="url" value={scrapeUrl} onChange={(e) => setScrapeUrl(e.target.value)} placeholder="https://forum-public.com/topic/12" style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', background: '#1e293b', color: '#fff', marginBottom: '0.8rem' }} required />
            <button type="submit" style={{ padding: '0.6rem 1.2rem', borderRadius: '6px', border: 'none', background: '#38bdf8', color: '#090d16', fontWeight: 'bold', cursor: 'pointer' }}>Lancer le Job</button>
          </form>
        </div>

        <div className="glass-card" style={{ padding: '1.2rem', borderRadius: '12px' }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1rem' }}>Recherche d'Images SearXNG</h3>
          <form onSubmit={handleStartSearch}>
            <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Pseudo / Nom + photo" style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', background: '#1e293b', color: '#fff', marginBottom: '0.8rem' }} required />
            <button type="submit" style={{ padding: '0.6rem 1.2rem', borderRadius: '6px', border: 'none', background: '#818cf8', color: '#090d16', fontWeight: 'bold', cursor: 'pointer' }}>Rechercher & Indexer</button>
          </form>
        </div>
      </div>

      {jobStatus && (
        <div className="glass-card" style={{ padding: '1.5rem', borderRadius: '12px', marginTop: '1.5rem' }}>
          <h3 style={{ marginTop: 0 }}>Statut du Job (#{jobStatus.job_id})</h3>
          <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
            <div>Cible : {jobStatus.target_url}</div>
            <div>Statut : <strong style={{ color: jobStatus.status === 'completed' ? '#34d399' : '#fbbf24' }}>{jobStatus.status.toUpperCase()}</strong></div>
            <div>Images trouvées : {jobStatus.total_images}</div>
            <div>Visages indexés : <strong>{jobStatus.faces_indexed}</strong></div>
            <div>Doublons ignorés (Sim &gt; 0.95) : {jobStatus.duplicates_skipped}</div>
            {Object.keys(jobStatus.errors_by_domain).length > 0 && (
              <div style={{ marginTop: '0.5rem', color: '#f87171' }}>
                Erreurs par domaine : {JSON.stringify(jobStatus.errors_by_domain)}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="glass-card" style={{ padding: '1.2rem', borderRadius: '12px', marginTop: '1.5rem' }}>
        <h3 style={{ marginTop: 0, fontSize: '1.1rem', color: '#f87171' }}>Droit à l'Oubli : Exclure un Domaine</h3>
        <form onSubmit={handleExcludeDomain} style={{ display: 'flex', gap: '0.5rem' }}>
          <input type="text" value={domainToExclude} onChange={(e) => setDomainToExclude(e.target.value)} placeholder="domaine-a-bannir.com" style={{ flex: 1, padding: '0.6rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', background: '#1e293b', color: '#fff' }} required />
          <button type="submit" style={{ padding: '0.6rem 1.2rem', borderRadius: '6px', border: 'none', background: '#ef4444', color: '#fff', fontWeight: 'bold', cursor: 'pointer' }}>Exclure & Purger</button>
        </form>
      </div>
    </div>
  );
}
