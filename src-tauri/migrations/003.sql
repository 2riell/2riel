CREATE TABLE purchase_lots(
  position_id TEXT NOT NULL REFERENCES market_positions(id),
  id TEXT NOT NULL,
  posted_date TEXT NOT NULL,
  entry_mode TEXT NOT NULL CHECK(entry_mode IN('amount','units')),
  price_micros INTEGER NOT NULL CHECK(price_micros>0),
  units_micros INTEGER NOT NULL CHECK(units_micros>0),
  amount_usd_minor INTEGER NOT NULL CHECK(amount_usd_minor>0),
  fee_usd_minor INTEGER NOT NULL CHECK(fee_usd_minor>=0),
  PRIMARY KEY(position_id,id)
);
PRAGMA user_version=3;
