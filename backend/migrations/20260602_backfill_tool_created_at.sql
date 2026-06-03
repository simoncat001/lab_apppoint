UPDATE `tool` t
LEFT JOIN (
  SELECT `tool_id`, MIN(`dt`) AS `inferred_created_at`
  FROM (
    SELECT `tool_id`, MIN(`start`) AS `dt`
    FROM `reservation`
    WHERE `tool_id` IS NOT NULL
    GROUP BY `tool_id`

    UNION ALL

    SELECT `tool_id`, MIN(`start`) AS `dt`
    FROM `usage_event`
    WHERE `tool_id` IS NOT NULL
    GROUP BY `tool_id`

    UNION ALL

    SELECT `tool_id`, MIN(`creation_time`) AS `dt`
    FROM `task`
    WHERE `tool_id` IS NOT NULL
    GROUP BY `tool_id`

    UNION ALL

    SELECT `tool_id`, MIN(`created_at`) AS `dt`
    FROM `tool_image`
    WHERE `tool_id` IS NOT NULL
    GROUP BY `tool_id`
  ) source_times
  WHERE `dt` IS NOT NULL
  GROUP BY `tool_id`
) inferred ON inferred.`tool_id` = t.`id`
SET t.`created_at` = inferred.`inferred_created_at`
WHERE t.`created_at` IS NULL
  AND inferred.`inferred_created_at` IS NOT NULL;
