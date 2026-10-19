CREATE TABLE market_positions(id TEXT PRIMARY KEY,symbol TEXT NOT NULL UNIQUE,units_micros INTEGER NOT NULL CHECK(units_micros>=0),data_json TEXT NOT NULL CHECK(json_valid(data_json)));
PRAGMA user_version=2;
