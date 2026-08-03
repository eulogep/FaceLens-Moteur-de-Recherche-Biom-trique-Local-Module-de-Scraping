import type { Job } from '../api/types'

const STATUS_LABELS: Record<Job['status'], string> = {
  pending: 'EN ATTENTE',
  running: 'EN COURS',
  completed: 'TERMINÉ',
  partial: 'PARTIEL',
  failed: 'ÉCHEC',
}

export function JobCard({ job }: { job: Job }) {
  const errors = Object.entries(job.errors_by_domain)
  const finished = ['completed', 'partial', 'failed'].includes(job.status)

  return (
    <article className="job-card" data-status={job.status}>
      <header>
        <div>
          <span className="eyebrow">JOB / {job.job_id}</span>
          <strong>{job.target_url}</strong>
        </div>
        <span className="job-status">{STATUS_LABELS[job.status]}</span>
      </header>

      <div className="job-progress" data-running={!finished}>
        <span style={{ width: finished ? '100%' : '42%' }} />
      </div>

      <div className="job-metrics">
        <span><b>IMAGES</b>{job.total_images}</span>
        <span><b>FACES</b>{job.faces_indexed}</span>
        <span><b>DOUBLONS</b>{job.duplicates_skipped}</span>
        <span><b>MAJ</b>{new Date(job.updated_at).toLocaleTimeString('fr-FR')}</span>
      </div>

      {errors.length > 0 && (
        <details className="job-errors">
          <summary>ERREURS PAR DOMAINE ({errors.length})</summary>
          {errors.map(([domain, message]) => (
            <p key={domain}><b>{domain}</b><span>{message}</span></p>
          ))}
        </details>
      )}
    </article>
  )
}
