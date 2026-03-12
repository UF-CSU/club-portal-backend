WITH questions AS (
    SELECT
        pq.id AS q_id,
        pq.created_at,
        pq.updated_at,
        pq.label,
        pq.description,
        pq.image,
        pq.is_required,
        pq.input_type,
        pq.field_id,
        pq.is_user_lookup,
        pq.link_user_field
    FROM public.polls_pollfield pf
    INNER JOIN public.polls_pollquestion pq
    ON pf.id = pq.field_id
    WHERE pf.poll_id = {{ poll_id }}
),
answers AS (
    SELECT *
    FROM questions qs
    INNER JOIN public.polls_pollquestionanswer pqa
    ON qs.q_id = pqa.question_id
)
SELECT
    q_id AS id,
    input_type,
    (
        SELECT COUNT(*)
        FROM answers
        WHERE answers.q_id = questions.q_id
    ) AS total_submissions,
    (
        SELECT json_agg(
            json_build_object(
                'user', ps.user_id,
                'text_value', ans.text_value,
                'options_value', (
                    ARRAY(
                        SELECT cio.label
                        FROM questions
                        JOIN public.polls_choiceinput ci
                        ON ans.question_id = ci.question_id
                        JOIN public.polls_choiceinputoption cio
                        ON ci.id = cio.input_id
                        WHERE ans.q_id = questions.q_id
                        AND questions.input_type = 'choice'
                    )
                ),
                'number_value', ans.number_value,
                'boolean_value', ans.boolean_value,
                'other_option_value', ans.other_option_value,
                'created_at', ps.created_at
            )
        )
        FROM answers ans
        INNER JOIN public.polls_pollsubmission ps
        ON ans.submission_id = ps.id
        WHERE ans.q_id = questions.q_id
    ) AS submissions,
    (
        SELECT json_build_object(
            'text_input', (
                SELECT json_build_object(
                    'average_words', AVG(len),
                    'max_words', MAX(len),
                    'min_words', MIN(len)
                )
                FROM (
                    SELECT array_length(regexp_split_to_array(trim(text_value), '\s+'), 1) AS len
                    FROM answers
                    WHERE answers.q_id = questions.q_id
                    AND questions.input_type = 'text'
                ) AS word_counts
            ),
            'email_input', (
                json_build_object(
                    'email_domains', (
                        SELECT ARRAY_AGG(DISTINCT regexp_replace(trim(text_value), '.*@', ''))
                        FROM answers
                        WHERE answers.q_id = questions.q_id
                        AND questions.input_type = 'email'
                    )
                )
            ),
            'checkbox_input', (
                json_build_object(
                    'total_true', (
                        SELECT COUNT(*)
                        FROM answers
                        WHERE answers.q_id = questions.q_id
                        AND questions.input_type = 'checkbox'
                        AND boolean_value = TRUE
                    )
                )
            ),
            'scale_input', (
                SELECT json_build_object(
                    'min_value', MIN(num),
                    'max_value', MAX(num),
                    'mean', AVG(num),
                    'median', (
                        SELECT PERCENTILE_CONT(0.5)
                        WITHIN GROUP (
                            ORDER BY num
                        )
                    )
                )
                FROM (
                    SELECT number_value AS num
                    FROM answers
                    WHERE answers.q_id = questions.q_id
                    AND questions.input_type = 'scale'
                ) AS nums
            ),
            'phone_input', (
                json_build_object(
                    'area_codes', (
                        ARRAY(
                            SELECT json_build_object(
                                'area_code', area_code,
                                'count', COUNT(area_code)
                            )
                            FROM (
                                SELECT SUBSTRING(text_value FROM '[^-]*') AS area_code
                                FROM answers
                                WHERE answers.q_id = questions.q_id
                                AND questions.input_type = 'phone'
                            ) AS area_codes
                            GROUP BY area_code
                        )
                    )
                )
            ),
            'number_input', (
                SELECT json_build_object(
                    'min_value', MIN(num),
                    'max_value', MAX(num),
                    'mean', AVG(num),
                    'median', (
                        SELECT PERCENTILE_CONT(0.5)
                        WITHIN GROUP (
                            ORDER BY num
                        )
                    )
                )
                FROM (
                    SELECT number_value AS num
                    FROM answers
                    WHERE answers.q_id = questions.q_id
                    AND questions.input_type = 'number'
                ) AS nums
            ),
            'url_input', (
                SELECT json_build_object(
                    'total_unique_domains', COUNT(unique_domain)
                )
                FROM (
                    SELECT DISTINCT SUBSTRING(text_value FROM '^.*?//(.*?)(?:/|$)') AS unique_domain
                    FROM answers
                    WHERE answers.q_id = questions.q_id
                    AND questions.input_type = 'url'
                ) AS unique_domains
            ),
            'upload_input', (
                json_build_object(
                    'file_types', (
                        ARRAY(
                            SELECT json_build_object(
                                'file_type', file_type,
                                'count', COUNT(file_type)
                            )
                            FROM (
                                SELECT SUBSTRING(cf.file FROM '\.(.*)') AS file_type
                                FROM answers
                                JOIN public.clubs_clubfile cf
                                ON answers.file_value_id = cf.id
                                WHERE answers.q_id = questions.q_id
                                AND questions.input_type = 'upload'
                            ) AS file_types
                            GROUP BY file_type
                        )
                    )
                )
            ),
            'date_input', (
                json_build_object(
                    'dates', (
                        ARRAY(
                            SELECT json_build_object(
                                'date', dte,
                                'count', COUNT(dte)
                            )
                            FROM (
                                SELECT text_value AS dte
                                FROM answers
                                WHERE answers.q_id = questions.q_id
                                AND questions.input_type = 'date'
                            ) AS dtes
                            GROUP BY dte
                        )
                    )
                )
            ),
            'time_input', (
                json_build_object(
                    'times', (
                        ARRAY(
                            SELECT json_build_object(
                                'time', tme,
                                'count', COUNT(tme)
                            )
                            FROM (
                                SELECT text_value AS tme
                                FROM answers
                                WHERE answers.q_id = questions.q_id
                                AND questions.input_type = 'time'
                            ) AS tmes
                            GROUP BY tme
                        )
                    )
                )
            ),
            'option_input', (
                json_build_object(
                    'options_submissions_count', (
                        ARRAY(
                            SELECT json_build_object(
                                'id', option_id,
                                'label', option_label,
                                'total_submissions', option_count
                            )
                            FROM (
                                SELECT cio.label AS option_label,
                                    cio.id AS option_id,
                                    COUNT(cio.id) as option_count
                                FROM (
                                    SELECT id AS ci_id, ci.question_id AS ci_qid
                                    FROM public.polls_choiceinput ci
                                    JOIN questions
                                    ON ci.question_id = questions.q_id
                                ) AS ci_id
                                JOIN public.polls_choiceinputoption cio
                                ON cio.input_id = ci_id
                                JOIN public.polls_pollquestionanswer_options_value pqa_o_v
                                ON cio.id = pqa_o_v.choiceinputoption_id
                                WHERE ci_qid = questions.q_id
                                    AND questions.input_type = 'choice'
                                GROUP BY cio.id
                            ) AS cios
                        )
                    )
                )
            )
        )
    ) AS analytics
FROM questions;
