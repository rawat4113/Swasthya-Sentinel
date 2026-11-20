def job_summary(job):
    return {'job_id':job.id,'source_type':job.source_type,'category':job.category,'filename':job.filename,'status':job.status,
            'total_rows':job.total_rows,'valid_rows':job.valid_rows,'invalid_rows':job.invalid_rows,'duplicate_rows':job.duplicate_rows,
            'imported_rows':job.imported_rows,'errors':job.errors,'preview':job.staged_data[:5],
            'created_at':job.created_at.isoformat() if job.created_at else None}
