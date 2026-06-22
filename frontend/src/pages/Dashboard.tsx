import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Sidebar } from '../components/layout/Sidebar';
import { TopBar } from '../components/layout/TopBar';
import './Dashboard.css';

interface ProjectSpec {
  component_ref: string;
  status: string;
  version: number;
  confidence: number;
  interconnections: string[];
  markdown: string;
}

export default function Dashboard() {
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('project') || '';

  const [specs, setSpecs] = useState<ProjectSpec[]>([]);
  const [notes, setNotes] = useState('');
  const [editingNotes, setEditingNotes] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (projectId) {
      loadProjectData();
    }
  }, [projectId]);

  const loadProjectData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch specs
      const specsRes = await fetch(`/api/specs/project-specs?project_id=${projectId}`);
      if (specsRes.ok) {
        const data = await specsRes.json();
        setSpecs(data.specs || []);
      }

      // Fetch notes
      const notesRes = await fetch(`/api/specs/project-notes?project_id=${projectId}`);
      if (notesRes.ok) {
        const data = await notesRes.json();
        setNotes(data.notes || '');
      }
    } catch (err) {
      console.error('Failed to load project data:', err);
      setError('Failed to load project data');
    } finally {
      setLoading(false);
    }
  };

  const saveNotes = async () => {
    try {
      const res = await fetch(`/api/specs/project-notes?project_id=${projectId}&notes=${encodeURIComponent(notes)}`, {
        method: 'POST',
      });
      if (res.ok) {
        setEditingNotes(false);
      }
    } catch (err) {
      console.error('Failed to save notes:', err);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-wrapper">
        <Sidebar />
        <div className="dashboard-page">
          <TopBar variant="default" />
          <div className="dashboard-content">
            <p>Loading dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  const verifiedCount = specs.filter((s) => s.status === 'verified').length;
  const avgConfidence = specs.length > 0
    ? (specs.reduce((sum, s) => sum + (s.confidence || 0), 0) / specs.length * 100).toFixed(0)
    : 0;

  return (
    <div className="dashboard-wrapper">
      <Sidebar />
      <div className="dashboard-page">
        <TopBar variant="default" />

        <div className="dashboard-content">
          <h1>Project Dashboard</h1>
          <p className="subtitle">Manage specs, notes, and interconnections</p>

          {error && <div className="error-message">{error}</div>}

          <div className="dashboard-grid">
            {/* Stats Panel */}
            <div className="dashboard-panel stats-panel">
              <h2>Project Stats</h2>
              <div className="stats">
                <div className="stat">
                  <span className="label">Total Specs</span>
                  <span className="value">{specs.length}</span>
                </div>
                <div className="stat">
                  <span className="label">Verified</span>
                  <span className="value">{verifiedCount}</span>
                </div>
                <div className="stat">
                  <span className="label">Avg Confidence</span>
                  <span className="value">{avgConfidence}%</span>
                </div>
              </div>
            </div>

            {/* Specs Panel */}
            <div className="dashboard-panel specs-panel">
              <h2>Generated Specs</h2>
              <div className="specs-list">
                {specs.length === 0 ? (
                  <p className="empty">No specs generated yet.</p>
                ) : (
                  specs.map((spec) => (
                    <div key={spec.component_ref} className="spec-card">
                      <div className="spec-header">
                        <h3>{spec.component_ref}</h3>
                        <span className={`status status-${spec.status}`}>
                          {spec.status || 'draft'}
                        </span>
                      </div>
                      <p className="spec-preview">
                        {spec.markdown?.substring(0, 80)}
                        {spec.markdown && spec.markdown.length > 80 ? '...' : ''}
                      </p>
                      <div className="spec-meta">
                        <span className="version">v{spec.version || 1}</span>
                        <span className="confidence">
                          {(spec.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      {spec.interconnections && spec.interconnections.length > 0 && (
                        <div className="interconnections">
                          <strong>Calls:</strong> {spec.interconnections.slice(0, 3).join(', ')}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Research Notes Panel */}
            <div className="dashboard-panel notes-panel">
              <div className="panel-header">
                <h2>Research Notes</h2>
                <button
                  className="btn btn-small"
                  onClick={() => {
                    if (editingNotes) saveNotes();
                    setEditingNotes(!editingNotes);
                  }}
                >
                  {editingNotes ? '✓ Save' : '✏️ Edit'}
                </button>
              </div>
              {editingNotes ? (
                <textarea
                  className="notes-input"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add notes about this project..."
                  rows={6}
                />
              ) : (
                <div className="notes-view">
                  {notes ? <p>{notes}</p> : <p className="empty">No notes yet. Click Edit to add some.</p>}
                </div>
              )}
            </div>

            {/* Interconnections Panel */}
            <div className="dashboard-panel interconnections-panel">
              <h2>Spec Interconnections</h2>
              <div className="interconnections-graph">
                {specs.filter((s) => s.interconnections?.length > 0).length === 0 ? (
                  <p className="empty">No interconnections found.</p>
                ) : (
                  <ul className="connection-list">
                    {specs
                      .filter((s) => s.interconnections?.length > 0)
                      .map((spec) => (
                        <li key={spec.component_ref}>
                          <strong>{spec.component_ref}</strong>
                          <span className="arrow">→</span>
                          <span className="connections">
                            {spec.interconnections.slice(0, 3).join(', ')}
                          </span>
                        </li>
                      ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
