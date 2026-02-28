CREATE OR REPLACE FUNCTION get_event_analytics(arg_event_id BIGINT)
RETURNS TABLE (
	-- Event info
	"event_id" BIGINT,
	"event_users_total" INT,
	"event_members_total" INT,
	"event_returning_total" INT,
	-- Previous event analytics
	"prev_id" BIGINT,
	"prev_users_total" INT,
	"prev_users_diff" NUMERIC,
	"prev_members_total" INT,
	"prev_members_diff" NUMERIC,
	"prev_returning_total" INT,
	"prev_returning_diff" NUMERIC,
	-- Event type analytics
	"evtype" VARCHAR,
	"evtype_events_count" INT,
	"evtype_users_avg" NUMERIC,
	"evtype_users_diff" NUMERIC,
	"evtype_members_avg" NUMERIC,
	"evtype_members_diff" NUMERIC,
	"evtype_returning_avg" NUMERIC,
	"evtype_returning_diff" NUMERIC,
	-- Recurring event analytics
	"rec_id" BIGINT,
	"rec_events_count" INT,
	"rec_users_avg" NUMERIC,
	"rec_users_diff" NUMERIC,
	"rec_members_avg" NUMERIC,
	"rec_members_diff" NUMERIC,
	"rec_returning_avg" NUMERIC,
	"rec_returning_diff" NUMERIC
) AS $$
BEGIN
	RETURN QUERY
	WITH 
	ev AS (
		SELECT ev.*, poll.id AS poll_id, poll.club_id AS poll_club_id
		FROM public.events_event AS ev
		JOIN public.polls_poll AS poll ON poll.event_id = ev.id
		WHERE ev.id = $1
	), 
	club_user_ids AS (
		SELECT DISTINCT user_id
		FROM public.clubs_clubmembership AS mem
		CROSS JOIN ev
		WHERE mem.club_id = ev.poll_club_id
	),
	club_other_subs AS (
		SELECT other_sub.id AS id, 
			other_poll.club_id AS club_id, 
			other_poll.id AS poll_id, 
			other_sub.user_id AS user_id, 
			other_event.id AS event_id,
			other_event.recurring_event_id AS event_recurring_event_id,
			other_event.start_at AS event_start_at, 
			other_event.event_type AS event_event_type
		FROM public.polls_pollsubmission AS other_sub
		CROSS JOIN ev
		JOIN public.polls_poll AS other_poll ON other_poll.id = other_sub.poll_id
		JOIN public.events_event AS other_event ON other_event.id = other_poll.event_id
		WHERE other_poll.club_id = ev.poll_club_id
			AND other_event.start_at < ev.start_at -- Submission to poll that took place before previous poll
			AND other_sub.poll_id != ev.poll_id -- Submission poll was not the current poll
	),
	prev_ev AS (
		SELECT ev2.*, prev_poll.id AS poll_id, prev_poll.club_id AS poll_club_id
		FROM ev
		JOIN public.events_event AS ev2 ON ev2.recurring_event_id = ev.recurring_event_id
		JOIN public.polls_poll AS prev_poll ON prev_poll.event_id = ev2.id
		WHERE ev2.id != ev.id
			AND ev2.start_at < ev.start_at
		GROUP BY ev2.id, prev_poll.id
		ORDER BY ev2.start_at DESC
		LIMIT 1
	),
	prev_subs AS (
		SELECT prev_ev.id AS event_id, 
			sub.user_id AS user_id, 
			sub.poll_id AS poll_id,
			prev_ev.start_at AS event_start_at
		FROM public.polls_pollsubmission AS sub
		JOIN prev_ev ON prev_ev.poll_id = sub.poll_id
		GROUP BY sub.user_id, prev_ev.id, sub.poll_id, prev_ev.start_at
	),
	evtype_events AS (
		SELECT evtype_ev.*
		FROM ev
		JOIN public.events_event AS evtype_ev ON evtype_ev.event_type = ev.event_type 
		JOIN public.polls_poll AS evtype_poll ON evtype_poll.event_id = evtype_ev.id
		WHERE evtype_poll.club_id = ev.poll_club_id 
			AND evtype_ev.id != ev.id
			AND evtype_ev.start_at < ev.start_at
		GROUP BY evtype_ev.id
	),
	rec_events AS (
		SELECT rec_ev.*
		FROM ev
		JOIN public.events_event AS rec_ev ON rec_ev.recurring_event_id = ev.recurring_event_id
		JOIN public.polls_poll AS rec_poll ON rec_poll.event_id = rec_ev.id
		WHERE rec_ev.id != ev.id
			AND rec_ev.start_at < ev.start_at
		GROUP BY rec_ev.id
	)
	SELECT
	-- Base event analytics
	$1 AS event_id,
	a.event_users_total::INT,
	a.event_members_total::INT,
	a.event_returning_total::INT,
	-- Previous event_type event
	a.prev_id,
	a.prev_users_total::INT,
	a.event_users_total::NUMERIC - a.prev_users_total::NUMERIC AS prev_users_diff,
	a.prev_members_total::INT,
	a.event_members_total::NUMERIC - a.prev_members_total::NUMERIC AS prev_members_diff,
	a.prev_returning_total::INT,
	a.event_returning_total::NUMERIC - a.prev_returning_total::NUMERIC AS prev_returning_diff,
	-- Event type analytics
	a.evtype,
	a.evtype_events_count::INT,
	a.evtype_users_avg::NUMERIC,
	a.event_users_total::NUMERIC - a.evtype_users_avg::NUMERIC AS evtype_users_diff,
	a.evtype_members_avg::NUMERIC,
	a.event_members_total::NUMERIC - a.evtype_members_avg::NUMERIC AS evtype_members_diff,
	a.evtype_returning_avg::NUMERIC,
	a.event_returning_total::NUMERIC - a.evtype_returning_avg::NUMERIC AS evtype_returning_diff,
	-- Recurring event analytics
	a.rec_id,
	a.rec_events_count::INT,
	a.rec_users_avg::NUMERIC,
	a.event_users_total::NUMERIC - a.rec_users_avg::NUMERIC AS rec_users_diff,
	a.rec_members_avg::NUMERIC,
	a.event_members_total::NUMERIC - a.rec_members_avg::NUMERIC AS rec_members_diff,
	a.rec_returning_avg::NUMERIC,
	a.event_returning_total::NUMERIC - a.rec_returning_avg::NUMERIC AS rec_returning_diff
	FROM (
		SELECT 
			-- Event analytics
			(
				SELECT COUNT(sub.user_id)
				FROM public.polls_pollsubmission AS sub
				CROSS JOIN ev
				WHERE sub.poll_id = ev.poll_id
			) as event_users_total,
			(
				SELECT COUNT(sub.user_id)
				FROM public.polls_pollsubmission AS sub
				CROSS JOIN ev
				WHERE sub.poll_id = ev.poll_id AND sub.user_id IN (
					SELECT user_id FROM club_user_ids
				)
			) as event_members_total,
			(
				SELECT COUNT(sub.user_id)
				FROM public.polls_pollsubmission AS sub
				CROSS JOIN ev
				WHERE ev.poll_id = sub.poll_id AND sub.user_id IN (
					SELECT user_id FROM club_other_subs
				)
			) as event_returning_total,
			-- Previous recurring event analytics
			(
				SELECT id FROM prev_ev
			) AS prev_id,
			(	
				SELECT COUNT(prev_subs.user_id) FROM prev_subs
			) AS prev_users_total,
			(
				SELECT COUNT(prev_subs.user_id) FROM prev_subs
				JOIN prev_ev ON prev_ev.id = prev_subs.event_id
				WHERE prev_subs.user_id IN (
					SELECT user_id FROM club_user_ids
				)
			) AS prev_members_total,
			(
				SELECT COUNT(prev_subs.user_id) FROM prev_subs
				WHERE prev_subs.user_id IN (
					SELECT user_id FROM club_other_subs
					WHERE club_other_subs.poll_id != prev_subs.poll_id
						AND club_other_subs.event_start_at < prev_subs.event_start_at
				)
			) AS prev_returning_total,
			-- Event type analytics
			ev.event_type AS evtype, 
			(
				SELECT COUNT(*) FROM evtype_events
			) AS evtype_events_count,
			(
				SELECT AVG(user_count)
				FROM (
					SELECT COUNT(sub.user_id) AS user_count
					FROM club_other_subs AS sub
					CROSS JOIN ev
					WHERE sub.event_event_type = ev.event_type
					GROUP BY sub.event_id
				) AS evtype_users_totals
			) AS evtype_users_avg,
			(
				SELECT AVG(user_count)
				FROM (
					SELECT COUNT(sub.user_id) AS user_count
					FROM club_other_subs AS sub
					CROSS JOIN ev
					WHERE sub.event_event_type = ev.event_type
						AND sub.user_id IN (
							SELECT user_id FROM club_user_ids
						)
					GROUP BY sub.event_id
				) AS evtype_members_counts
			) AS evtype_members_avg,
			(
				SELECT AVG(user_count)
				FROM (
					SELECT COUNT(sub.user_id) AS user_count
					FROM club_other_subs AS sub
					CROSS JOIN ev
					WHERE sub.event_event_type = ev.event_type
						-- Check if there is an existing submission from a previous event from that user
						AND EXISTS ( 
							SELECT other_sub.id
							FROM club_other_subs AS other_sub
							WHERE other_sub.event_start_at < sub.event_start_at
								AND other_sub.user_id = sub.user_id
								AND other_sub.event_id != sub.event_id
						)
					GROUP BY sub.event_id
				) AS evtype_returning_users_counts
			) AS evtype_returning_avg,
			-- Recurring event analytics
			ev.recurring_event_id AS rec_id,
			(
				SELECT COUNT(rec_events.id) FROM rec_events
			) AS rec_events_count,
			(	
				SELECT AVG(user_count)
				FROM (
					SELECT COUNT(sub.user_id) AS user_count
					FROM club_other_subs AS sub
					CROSS JOIN ev
					WHERE sub.event_recurring_event_id = ev.recurring_event_id
						AND sub.event_start_at < ev.start_at
					GROUP BY sub.event_id
				) AS rec_users_counts
			) AS rec_users_avg,
			(
				SELECT AVG(user_count)
				FROM (
					SELECT COUNT(sub.user_id) AS user_count
					FROM club_other_subs AS sub
					JOIN rec_events ON rec_events.id = sub.event_id
						AND sub.event_start_at < ev.start_at
						AND sub.user_id IN (
							SELECT user_id FROM club_user_ids
						)
					GROUP BY sub.event_id
				) AS rec_members_counts
			) AS rec_members_avg,
			(
				SELECT AVG(user_count)
				FROM (
					SELECT COUNT(sub.user_id) AS user_count
					FROM club_other_subs AS sub
					JOIN rec_events ON rec_events.id = sub.event_id
						-- Check if there is an existing submission from a previous event from that user
						AND EXISTS ( 
							SELECT other_sub.id
							FROM club_other_subs AS other_sub
							WHERE other_sub.event_start_at < sub.event_start_at
								AND other_sub.user_id = sub.user_id
								AND other_sub.event_id != sub.event_id
						)
					GROUP BY sub.event_id
				) AS rec_returning_users_counts
			) AS rec_returning_avg
		FROM public.events_event AS ev
		JOIN public.polls_poll AS poll ON poll.event_id = ev.id
		WHERE ev.id = $1
	) AS a;
END;
$$ LANGUAGE plpgsql;
