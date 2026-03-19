WITH ts AS (
    SELECT pb.created_at AS init, p.close_at AS closed
    FROM public.polls_pollbase pb
    JOIN public.polls_poll p ON p.id = pb.id
    WHERE pb.id = {{ poll_id }}
)
SELECT json_object_agg(
    start_interval, submission_count
) AS submissions_heatmap
FROM (
    SELECT gs.interval_start AS start_interval, COUNT(ps.created_at) AS submission_count
    FROM ts, generate_series(
        ts.init,
        COALESCE(ts.closed, ts.init + INTERVAL '{{ interval_limit }}'),
        INTERVAL '{{ bin_interval }}'
    ) as gs(interval_start)
    LEFT JOIN public.polls_pollsubmission ps
    ON ps.updated_at >= gs.interval_start
        AND ps.updated_at < gs.interval_start + INTERVAL '{{ bin_interval }}'
        AND ps.poll_id = {{ poll_id }}
    GROUP BY gs.interval_start
    ORDER BY gs.interval_start
) AS heatmap;
