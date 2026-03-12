SELECT COUNT(*) AS total_guest_users FROM public.polls_pollsubmission
WHERE public.polls_pollsubmission.poll_id = {{ poll_id }}
AND user_id NOT IN (
    SELECT DISTINCT user_id FROM public.clubs_clubmembership
    JOIN public.polls_poll ON public.polls_poll.club_id = public.clubs_clubmembership.club_id
    WHERE public.polls_poll.id = {{ poll_id }}
);