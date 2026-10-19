PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS app_state(singleton INTEGER PRIMARY KEY CHECK(singleton=1),revision INTEGER NOT NULL CHECK(revision>=0),json TEXT NOT NULL CHECK(json_valid(json)));
CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, name TEXT NOT NULL, institution TEXT NOT NULL, kind TEXT NOT NULL, currency TEXT NOT NULL CHECK(currency='PHP'), opening INTEGER NOT NULL, opened TEXT NOT NULL, included INTEGER NOT NULL, archived INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS entries(id TEXT PRIMARY KEY,date TEXT NOT NULL,description TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN('income','expense','refund','transfer','adjustment')),account_id TEXT NOT NULL REFERENCES accounts(id),destination_id TEXT REFERENCES accounts(id),amount INTEGER NOT NULL,fee INTEGER NOT NULL CHECK(fee>=0),category TEXT NOT NULL,source TEXT NOT NULL,import_key TEXT UNIQUE,CHECK(kind='adjustment' OR amount>0),CHECK(kind!='transfer' OR (destination_id IS NOT NULL AND destination_id!=account_id)));
CREATE TABLE IF NOT EXISTS budgets(id TEXT PRIMARY KEY,category TEXT NOT NULL,month TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0));
CREATE TABLE IF NOT EXISTS goals(id TEXT PRIMARY KEY,name TEXT NOT NULL,account_id TEXT NOT NULL REFERENCES accounts(id),target INTEGER NOT NULL CHECK(target>0),allocated INTEGER NOT NULL CHECK(allocated>=0),due TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id),date TEXT NOT NULL,actual INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS audit(sequence INTEGER PRIMARY KEY,at TEXT NOT NULL,previous_json TEXT NOT NULL,new_json TEXT NOT NULL);
PRAGMA user_version=1;
