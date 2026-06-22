import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { TopBar } from '../components/layout/TopBar'
import { AmbientGrid } from '../components/layout/AmbientGrid'
import { GroupTree } from '../components/explore/GroupTree'
import { GroupDetail } from '../components/explore/GroupDetail'
import { useGroups, useGroup } from '../api/useGroups'
import './RepoExplore.css'

export function RepoExplore() {
  const { repoId = 'default' } = useParams()
  const [selectedId, setSelectedId] = useState<string>('')
  const { data: groups, isLoading: groupsLoading, error: groupsError } = useGroups()
  const { data: groupDetail, isLoading: detailLoading, error: detailError } = useGroup(selectedId)

  // Auto-select first group if available
  if (groups && groups.length > 0 && !selectedId) {
    setSelectedId(groups[0].id)
  }

  return (
    <div className="repo-explore-page">
      <AmbientGrid />
      <TopBar variant="workspace" />

      <main className="repo-explore-main">
        {groupsError && (
          <div className="error-message" role="alert">
            <strong>Error loading groups:</strong> {groupsError.message}
          </div>
        )}

        {groupsLoading ? (
          <div className="loading-state">
            <div className="spinner" />
            <p>Loading group tree...</p>
          </div>
        ) : groups ? (
          <div className="explore-content">
            <GroupTree groups={groups} activeId={selectedId} onSelect={setSelectedId} />

            <div className="detail-pane">
              {detailError && (
                <div className="error-message" role="alert">
                  <strong>Error loading group:</strong> {detailError.message}
                </div>
              )}

              {detailLoading ? (
                <div className="loading-state">
                  <div className="spinner" />
                  <p>Loading group detail...</p>
                </div>
              ) : groupDetail ? (
                <GroupDetail group={groupDetail} repoId={repoId} />
              ) : (
                <div className="empty-state">
                  <p>Select a group to view details</p>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </main>
    </div>
  )
}

export default RepoExplore
