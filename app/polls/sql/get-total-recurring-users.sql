SELECT COUNT(*) AS total_recurring_users
FROM (
    SELECT ps.user_id
    FROM public.polls_pollsubmission ps
    JOIN public.polls_poll p ON p.id = ps.poll_id
    WHERE p.club_id = {{ club_id }}
    GROUP BY ps.user_id
    HAVING COUNT(*) > 1
) _;
