-- Run once on existing installations; preserves all rows and can be repeated.
ALTER TABLE portfolio_traders
    ADD COLUMN IF NOT EXISTS strategy_params JSONB NOT NULL DEFAULT '{}'::jsonb;
