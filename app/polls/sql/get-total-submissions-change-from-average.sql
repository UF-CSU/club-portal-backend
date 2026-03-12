WITH values AS (
    SELECT
        (
            SELECT COUNT(*)
            FROM public.polls_pollsubmission ps
            WHERE ps.poll_id = {{ poll_id }}
        ) AS main_poll_count,
    COALESCE
    (
        (
            SELECT AVG(c) FROM (
            SELECT COUNT(*) AS c
            FROM public.polls_pollsubmission ps
            JOIN public.polls_poll p
                ON p.id = ps.poll_id
            WHERE p.club_id = {{ club_id }}
                AND p.id <> {{ poll_id }}
            GROUP BY ps.poll_id
            ) _
        ),
        0
    ) AS poll_average_count
)
SELECT
    CASE
        WHEN poll_average_count = 0 THEN 0
        ELSE (main_poll_count - poll_average_count) / poll_average_count
    END AS total_submissions_change_from_average
FROM values;
