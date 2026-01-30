-- Migration: Make activity_logs.storyboard_id required
-- Created: 2026-01-30
-- Reason: Enforce data integrity - all activity logs must belong to a storyboard

-- Step 1: Check how many NULL records exist
SELECT COUNT(*) AS null_count
FROM activity_logs
WHERE storyboard_id IS NULL;

-- Step 2: Delete NULL records (or update with a default storyboard_id)
-- Option A: Delete NULL records
DELETE FROM activity_logs WHERE storyboard_id IS NULL;

-- Option B (Alternative): Update with a default storyboard_id
-- UPDATE activity_logs
-- SET storyboard_id = 1  -- Replace with actual default storyboard ID
-- WHERE storyboard_id IS NULL;

-- Step 3: Add NOT NULL constraint
ALTER TABLE activity_logs
ALTER COLUMN storyboard_id SET NOT NULL;

-- Verification: This should return 0
SELECT COUNT(*)
FROM activity_logs
WHERE storyboard_id IS NULL;
