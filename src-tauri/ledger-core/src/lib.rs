use rusqlite::{params, Connection};
use serde_json::{json, Value};
fn text<'a>(v: &'a Value, k: &str) -> Result<&'a str, String> {
    v[k].as_str().ok_or(format!("Invalid {k}"))
}
fn integer(v: &Value, k: &str) -> Result<i64, String> {
    let n = v[k].as_i64().ok_or(format!("Invalid {k}"))?;
    if !(-9_000_000_000_000_000..=9_000_000_000_000_000).contains(&n) {
        return Err("Amount exceeds precision limit".into());
    }
    Ok(n)
}
fn err(e: impl std::fmt::Display) -> String {
    e.to_string()
}

fn date(v: &Value, k: &str, future: bool) -> Result<(), String> {
    let value = text(v, k)?;
    let parsed =
        chrono::NaiveDate::parse_from_str(value, "%Y-%m-%d").map_err(|_| format!("Invalid {k}"))?;
    if parsed.format("%Y-%m-%d").to_string() != value {
        return Err(format!("Invalid {k}"));
    }
    let today = (chrono::Utc::now() + chrono::Duration::hours(8)).date_naive();
    if !future && parsed > today {
        return Err("Only posted dates are supported".into());
    }
    Ok(())
}
fn valid_market_symbol(s: &str) -> bool {
    let mut parts = s.split(['.', '-']);
    let base = parts.next().unwrap_or("");
    if base.is_empty()
        || base.len() > 10
        || !base.as_bytes()[0].is_ascii_uppercase()
        || !base
            .bytes()
            .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit())
    {
        return false;
    }
    let class = parts.next();
    matches!(class, None | Some("A") | Some("B")) && parts.next().is_none()
}
fn validate_purchases(p: &Value) -> Result<(), String> {
    let Some(value) = p.get("purchases") else {
        return Ok(());
    };
    let lots = value.as_array().ok_or("Invalid purchase records")?;
    if lots.len() > 200 {
        return Err("Maximum 200 purchases per symbol".into());
    }
    let mut ids = std::collections::HashSet::new();
    let mut units_total = 0i128;
    let mut cost_total = 0i128;
    for lot in lots {
        let id = text(lot, "id")?;
        if id.is_empty() || !ids.insert(id) {
            return Err("Invalid/duplicate purchase ID".into());
        }
        date(lot, "date", false)?;
        let units = integer(lot, "unitsMicros")?;
        let price = integer(lot, "priceMicros")?;
        let amount = integer(lot, "amountUsdMinor")?;
        let fee = integer(lot, "feeUsdMinor")?;
        if !(1..=1_000_000_000_000).contains(&units)
            || !(1..=1_000_000_000_000).contains(&price)
            || amount <= 0
            || fee < 0
        {
            return Err("Invalid purchase amount, quantity, price or fee".into());
        }
        let consistent = match text(lot, "entryMode")? {
            "amount" => units as i128 == amount as i128 * 10_000_000_000 / price as i128,
            "units" => {
                amount as i128 == (units as i128 * price as i128 + 5_000_000_000) / 10_000_000_000
            }
            _ => false,
        };
        if !consistent {
            return Err("Purchase amount, price and units do not match".into());
        }
        units_total += units as i128;
        cost_total += amount as i128 + fee as i128;
    }
    if !lots.is_empty()
        && (units_total > 1_000_000_000_000
            || cost_total > 9_000_000_000_000_000
            || integer(p, "unitsMicros")? as i128 != units_total
            || integer(p, "costBasisUsdMinor")? as i128 != cost_total)
    {
        return Err("Position totals must equal purchase records".into());
    }
    Ok(())
}
fn market_validate(v: &Value) -> Result<(), String> {
    let Some(m) = v.get("market") else {
        return Ok(());
    };
    if m["enabled"].as_bool().is_none() || m["autoRefresh"].as_bool().is_none() {
        return Err("Invalid market preferences".into());
    }
    let ps = m["positions"]
        .as_array()
        .ok_or("Invalid market watchlist")?;
    if ps.len() > 10 {
        return Err("Watchlist is limited to 10 symbols".into());
    }
    let mut symbols = std::collections::HashSet::new();
    let mut ids = std::collections::HashSet::new();
    let mut total = 0i128;
    for p in ps {
        let symbol = text(p, "symbol")?;
        if !valid_market_symbol(symbol) || !symbols.insert(symbol) || !ids.insert(text(p, "id")?) {
            return Err("Invalid/duplicate market symbol or ID".into());
        }
        if text(p, "name")?.trim().is_empty() {
            return Err("Position name required".into());
        }
        validate_purchases(p)?;
        let units = integer(p, "unitsMicros")?;
        if !(0..=1_000_000_000_000).contains(&units) {
            return Err("Invalid position quantity".into());
        }
        if !p["costBasisUsdMinor"].is_null() && integer(p, "costBasisUsdMinor")? < 0 {
            return Err("Invalid cost basis".into());
        }
        if !p["quote"].is_null() {
            let q = &p["quote"];
            let price = integer(q, "priceMicros")?;
            if text(q, "symbol")? != symbol
                || !(1..=1_000_000_000_000).contains(&price)
                || !["manual", "finnhub"].contains(&text(q, "provider")?)
            {
                return Err("Invalid market quote".into());
            }
            let ts = integer(q, "timestamp")?;
            if ts <= 0 || ts > chrono::Utc::now().timestamp() + 300 {
                return Err("Invalid quote timestamp".into());
            }
            chrono::DateTime::parse_from_rfc3339(text(q, "receivedAt")?)
                .map_err(|_| "Invalid quote receipt time")?;
            if !q["previousCloseMicros"].is_null()
                && !(0..=1_000_000_000_000).contains(&integer(q, "previousCloseMicros")?)
            {
                return Err("Invalid previous price".into());
            }
            total += (units as i128 * price as i128 + 5_000_000_000) / 10_000_000_000;
        }
    }
    if total > 9_000_000_000_000_000 {
        return Err("Market valuation exceeds precision limit".into());
    }
    if !m["fx"].is_null() {
        let fx = &m["fx"];
        let rate = integer(fx, "rateMicros")?;
        date(fx, "date", false)?;
        if !(1..=1_000_000_000_000).contains(&rate)
            || (total * rate as i128 + 500_000) / 1_000_000 > 9_000_000_000_000_000
        {
            return Err("FX valuation exceeds precision limit".into());
        }
    }
    Ok(())
}

fn validate(v: &Value) -> Result<(), String> {
    for key in [
        "accounts",
        "entries",
        "budgets",
        "goals",
        "snapshots",
        "audit",
    ] {
        if !v[key].is_array() {
            return Err(format!("Invalid {key}"));
        }
    }
    for a in v["accounts"].as_array().unwrap() {
        let kind = text(a, "type")?;
        if ![
            "cash",
            "savings",
            "checking",
            "e-wallet",
            "investment cash",
            "credit card",
            "loan",
            "other asset",
            "other liability",
        ]
        .contains(&kind)
        {
            return Err("Unsupported account type".into());
        }
        let name = text(a, "name")?;
        if name.trim().is_empty() || name.len() > 400 {
            return Err("Invalid account name".into());
        }
        date(a, "opened", false)?;
    }
    for e in v["entries"].as_array().unwrap() {
        date(e, "date", false)?;
        let description = text(e, "description")?;
        if description.trim().is_empty() || description.len() > 800 {
            return Err("Invalid description".into());
        }
        if !["manual", "csv", "reconciliation"].contains(&text(e, "source")?) {
            return Err("Invalid entry source".into());
        }
    }
    for b in v["budgets"].as_array().unwrap() {
        let month = text(b, "month")?;
        let d = json!({"date":format!("{month}-01")});
        date(&d, "date", true)?;
    }
    for g in v["goals"].as_array().unwrap() {
        date(g, "due", true)?;
        if text(g, "name")?.trim().is_empty() {
            return Err("Goal name required".into());
        }
    }
    for snap in v["snapshots"].as_array().unwrap() {
        date(snap, "date", false)?;
    }
    for event in v["audit"].as_array().unwrap() {
        text(event, "at")?;
        text(event, "action")?;
    }
    market_validate(v)?;
    // Use wider integer arithmetic to reject ledgers that JavaScript cannot represent exactly.
    let mut worth = 0i128;
    for a in v["accounts"].as_array().unwrap() {
        let account = text(a, "id")?;
        let mut balance = integer(a, "opening")? as i128;
        for e in v["entries"].as_array().unwrap() {
            let amount = integer(e, "amount")? as i128;
            let kind = text(e, "kind")?;
            if text(e, "account")? == account {
                balance += if kind == "expense" || kind == "transfer" {
                    -amount
                } else {
                    amount
                };
                balance -= integer(e, "fee")? as i128;
            }
            if kind == "transfer" && e["to"].as_str() == Some(account) {
                balance += amount;
            }
        }
        if balance.abs() > 9_000_000_000_000_000 {
            return Err("Account total exceeds precision limit".into());
        }
        if a["include"].as_bool() == Some(true) {
            worth += balance;
        }
    }
    if worth.abs() > 9_000_000_000_000_000 {
        return Err("Net worth exceeds precision limit".into());
    }
    Ok(())
}

fn quote_only_update(before: &Value, after: &Value) -> bool {
    let Some(old) = before["market"]["positions"].as_array() else {
        return false;
    };
    let Some(new) = after["market"]["positions"].as_array() else {
        return false;
    };
    let mut changed = false;
    for p in new {
        let Some(prior) = old.iter().find(|x| x["id"] == p["id"]) else {
            return false;
        };
        if prior["quote"] != p["quote"] {
            changed = true;
            if p["quote"]["provider"].as_str() != Some("finnhub") {
                return false;
            }
        }
    }
    if !changed {
        return false;
    }

    let mut a = before.clone();
    let mut b = after.clone();
    for v in [&mut a, &mut b] {
        let Some(root) = v.as_object_mut() else {
            return false;
        };
        root.remove("revision");
        root.remove("audit");
        let Some(ps) = v["market"]["positions"].as_array_mut() else {
            return false;
        };
        for p in ps {
            let Some(object) = p.as_object_mut() else {
                return false;
            };
            object.remove("quote");
        }
    }
    a == b && before["market"] != after["market"]
}
pub fn save(db: &mut Connection, json: String, expected_revision: i64) -> Result<(), String> {
    if json.len() > 10_000_000 {
        return Err("Database update too large".into());
    }
    let v: Value = serde_json::from_str(&json).map_err(err)?;
    validate(&v)?;
    let revision = integer(&v, "revision")?;
    if revision != expected_revision + 1 {
        return Err("Invalid revision".into());
    }
    let tx = db.transaction().map_err(err)?;
    let (current, previous): (i64, String) = tx
        .query_row(
            "SELECT revision,json FROM app_state WHERE singleton=1",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .map_err(err)?;
    if current != expected_revision {
        return Err("Data changed in another window. Reload before saving.".into());
    }
    if v["onboarded"].as_bool().is_none() {
        return Err("Invalid onboarding state".into());
    }
    for table in [
        "purchase_lots",
        "market_positions",
        "entries",
        "goals",
        "snapshots",
        "budgets",
        "accounts",
    ] {
        tx.execute(&format!("DELETE FROM {table}"), [])
            .map_err(err)?;
    }
    for a in v["accounts"].as_array().ok_or("Invalid accounts")? {
        let opening = integer(a, "opening")?;
        let kind = text(a, "type")?;
        if ["credit card", "loan", "other liability"].contains(&kind) && opening > 0 {
            return Err("Liabilities must open with negative balances".into());
        }
        tx.execute(
            "INSERT INTO accounts VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9)",
            params![
                text(a, "id")?,
                text(a, "name")?,
                text(a, "institution")?,
                kind,
                text(a, "currency")?,
                opening,
                text(a, "opened")?,
                a["include"].as_bool().ok_or("Invalid inclusion")?,
                a["archived"].as_bool().ok_or("Invalid archive")?
            ],
        )
        .map_err(err)?;
    }
    for e in v["entries"].as_array().ok_or("Invalid entries")? {
        tx.execute(
            "INSERT INTO entries VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)",
            params![
                text(e, "id")?,
                text(e, "date")?,
                text(e, "description")?,
                text(e, "kind")?,
                text(e, "account")?,
                e["to"].as_str(),
                integer(e, "amount")?,
                integer(e, "fee")?,
                text(e, "category")?,
                text(e, "source")?,
                e["importKey"].as_str()
            ],
        )
        .map_err(err)?;
    }
    let invalid:i64=tx.query_row("SELECT count(*) FROM entries e JOIN accounts a ON a.id=e.account_id LEFT JOIN accounts d ON d.id=e.destination_id WHERE e.date<a.opened OR (e.kind='transfer' AND e.date<d.opened)",[],|r|r.get(0)).map_err(err)?;
    if invalid > 0 {
        return Err("Transaction predates opening balance".into());
    }
    for b in v["budgets"].as_array().ok_or("Invalid budgets")? {
        tx.execute(
            "INSERT INTO budgets VALUES(?1,?2,?3,?4)",
            params![
                text(b, "id")?,
                text(b, "category")?,
                text(b, "month")?,
                integer(b, "limit")?
            ],
        )
        .map_err(err)?;
    }
    for g in v["goals"].as_array().ok_or("Invalid goals")? {
        tx.execute(
            "INSERT INTO goals VALUES(?1,?2,?3,?4,?5,?6)",
            params![
                text(g, "id")?,
                text(g, "name")?,
                text(g, "account")?,
                integer(g, "target")?,
                integer(g, "allocated")?,
                text(g, "due")?
            ],
        )
        .map_err(err)?;
    }
    for s in v["snapshots"].as_array().ok_or("Invalid snapshots")? {
        tx.execute(
            "INSERT INTO snapshots VALUES(?1,?2,?3,?4)",
            params![
                text(s, "id")?,
                text(s, "account")?,
                text(s, "date")?,
                integer(s, "actual")?
            ],
        )
        .map_err(err)?;
    }
    if let Some(positions) = v["market"]["positions"].as_array() {
        for p in positions {
            tx.execute(
                "INSERT INTO market_positions VALUES(?1,?2,?3,?4)",
                params![
                    text(p, "id")?,
                    text(p, "symbol")?,
                    integer(p, "unitsMicros")?,
                    p.to_string()
                ],
            )
            .map_err(err)?;
            if let Some(lots) = p["purchases"].as_array() {
                for lot in lots {
                    tx.execute(
                        "INSERT INTO purchase_lots VALUES(?1,?2,?3,?4,?5,?6,?7,?8)",
                        params![
                            text(p, "id")?,
                            text(lot, "id")?,
                            text(lot, "date")?,
                            text(lot, "entryMode")?,
                            integer(lot, "priceMicros")?,
                            integer(lot, "unitsMicros")?,
                            integer(lot, "amountUsdMinor")?,
                            integer(lot, "feeUsdMinor")?
                        ],
                    )
                    .map_err(err)?;
                }
            }
        }
    }
    let over:i64=tx.query_row("SELECT count(*) FROM (SELECT g.account_id,sum(g.allocated) AS reserved FROM goals g GROUP BY g.account_id) x JOIN accounts a ON a.id=x.account_id WHERE reserved > max(0,a.opening+coalesce((SELECT sum(CASE WHEN e.account_id=a.id THEN (CASE WHEN e.kind IN ('expense','transfer') THEN -e.amount ELSE e.amount END)-e.fee ELSE 0 END + CASE WHEN e.kind='transfer' AND e.destination_id=a.id THEN e.amount ELSE 0 END) FROM entries e WHERE e.account_id=a.id OR e.destination_id=a.id),0))",[],|r|r.get(0)).map_err(err)?;
    if over > 0 {
        return Err("Goal allocations exceed available funds".into());
    }
    let before: Value = serde_json::from_str(&previous).map_err(err)?;
    // Provider price refreshes are non-ledger observations. Avoid duplicating the
    // complete financial database in audit every minute; financial edits still audit fully.
    if !quote_only_update(&before, &v) {
        tx.execute(
            "INSERT INTO audit(at,previous_json,new_json) VALUES(datetime('now'),?1,?2)",
            params![previous, json],
        )
        .map_err(err)?;
    }
    tx.execute(
        "UPDATE app_state SET revision=?1,json=?2 WHERE singleton=1",
        params![revision, json],
    )
    .map_err(err)?;
    tx.commit().map_err(err)
}
pub fn open(path: impl AsRef<std::path::Path>, key: &str) -> Result<Connection, String> {
    if key.len() != 64 || !key.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("Invalid encryption key".into());
    }
    let db = Connection::open(path).map_err(err)?;
    db.execute_batch(&format!("PRAGMA key=\"x'{key}'\"; PRAGMA foreign_keys=ON; PRAGMA journal_mode=DELETE; PRAGMA secure_delete=ON;")).map_err(err)?;
    let _: String = db
        .query_row("PRAGMA cipher_version", [], |r| r.get(0))
        .map_err(|_| "SQLCipher required; refusing plaintext storage".to_string())?;
    let version: i64 = db
        .query_row("PRAGMA user_version", [], |r| r.get(0))
        .map_err(err)?;
    if version > 3 {
        return Err("Database was created by a newer SALDO version".into());
    }
    if version == 0 {
        db.execute_batch(concat!(
            "BEGIN IMMEDIATE;",
            include_str!("../../migrations/001.sql"),
            "COMMIT;"
        ))
        .map_err(err)?;
    }
    if version < 2 {
        db.execute_batch(concat!(
            "BEGIN IMMEDIATE;",
            include_str!("../../migrations/002.sql"),
            "COMMIT;"
        ))
        .map_err(err)?;
    }
    if version < 3 {
        db.execute_batch(concat!(
            "BEGIN IMMEDIATE;",
            include_str!("../../migrations/003.sql"),
            "COMMIT;"
        ))
        .map_err(err)?;
    }
    let initial = json!({"revision":0,"onboarded":false,"accounts":[],"entries":[],"budgets":[],"goals":[],"snapshots":[],"audit":[]});
    db.execute(
        "INSERT OR IGNORE INTO app_state VALUES(1,0,?1)",
        [initial.to_string()],
    )
    .map_err(err)?;
    Ok(db)
}
#[cfg(test)]
mod tests {
    use super::*;
    fn state() -> Value {
        json!({"revision":1,"onboarded":true,"accounts":[{"id":"a","name":"Cash","institution":"Cash","type":"cash","currency":"PHP","opening":10000,"opened":"2026-01-01","include":true,"archived":false},{"id":"b","name":"Savings","institution":"Bank","type":"savings","currency":"PHP","opening":0,"opened":"2026-01-01","include":true,"archived":false}],"entries":[],"budgets":[],"goals":[],"snapshots":[],"audit":[]})
    }
    fn memory() -> Connection {
        open(":memory:", &"12".repeat(32)).unwrap()
    }
    #[test]
    fn migrations_and_persistence() {
        let mut db = memory();
        save(&mut db, state().to_string(), 0).unwrap();
        let count: i64 = db
            .query_row("SELECT count(*) FROM accounts", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 2);
        let audit: i64 = db
            .query_row("SELECT count(*) FROM audit", [], |r| r.get(0))
            .unwrap();
        assert_eq!(audit, 1);
    }
    #[test]
    fn stale_write_is_rejected() {
        let mut db = memory();
        save(&mut db, state().to_string(), 0).unwrap();
        assert!(save(&mut db, state().to_string(), 0)
            .unwrap_err()
            .contains("another window"));
    }
    #[test]
    fn invalid_transfer_rolls_back_everything() {
        let mut db = memory();
        let mut s = state();
        s["entries"] = json!([{"id":"x","date":"2026-01-02","description":"Transfer","kind":"transfer","account":"a","to":"a","amount":100,"fee":0,"category":"Bills","source":"manual"}]);
        assert!(save(&mut db, s.to_string(), 0).is_err());
        let rev: i64 = db
            .query_row("SELECT revision FROM app_state", [], |r| r.get(0))
            .unwrap();
        assert_eq!(rev, 0);
        let count: i64 = db
            .query_row("SELECT count(*) FROM accounts", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 0);
    }
    #[test]
    fn duplicate_import_key_is_rejected() {
        let mut db = memory();
        let mut s = state();
        s["entries"] = json!([{"id":"x","date":"2026-01-02","description":"Lunch","kind":"expense","account":"a","amount":100,"fee":0,"category":"Food","source":"csv","importKey":"same"},{"id":"y","date":"2026-01-02","description":"Lunch","kind":"expense","account":"a","amount":100,"fee":0,"category":"Food","source":"csv","importKey":"same"}]);
        assert!(save(&mut db, s.to_string(), 0).is_err());
    }
    #[test]
    fn allocations_cannot_exceed_funds() {
        let mut db = memory();
        let mut s = state();
        s["goals"] = json!([{"id":"g","name":"Goal","account":"a","target":50000,"allocated":10001,"due":"2026-12-31"}]);
        assert!(save(&mut db, s.to_string(), 0)
            .unwrap_err()
            .contains("exceed"));
    }
    #[test]
    fn encrypted_file_requires_correct_key() {
        let path = std::env::temp_dir().join(format!(
            "saldo-test-{}-{}.db",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        {
            let mut db = open(&path, &"12".repeat(32)).unwrap();
            save(&mut db, state().to_string(), 0).unwrap();
        }
        let bytes = std::fs::read(&path).unwrap();
        assert_ne!(&bytes[..16], b"SQLite format 3\0");
        assert!(open(&path, &"34".repeat(32)).is_err());
        let db = open(&path, &"12".repeat(32)).unwrap();
        let count: i64 = db
            .query_row("SELECT count(*) FROM accounts", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 2);
        drop(db);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn migrates_v1_without_losing_financial_records() {
        let path = std::env::temp_dir().join(format!(
            "saldo-migrate-{}-{}.db",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap()
        ));
        let key = "12".repeat(32);
        {
            let mut db = open(&path, &key).unwrap();
            save(&mut db, state().to_string(), 0).unwrap();
            db.execute_batch(
                "DROP TABLE purchase_lots; DROP TABLE market_positions; PRAGMA user_version=1;",
            )
            .unwrap();
        }
        let db = open(&path, &key).unwrap();
        let version: i64 = db
            .query_row("PRAGMA user_version", [], |r| r.get(0))
            .unwrap();
        assert_eq!(version, 3);
        let accounts: i64 = db
            .query_row("SELECT count(*) FROM accounts", [], |r| r.get(0))
            .unwrap();
        assert_eq!(accounts, 2);
        let audit: i64 = db
            .query_row("SELECT count(*) FROM audit", [], |r| r.get(0))
            .unwrap();
        assert_eq!(audit, 1);
        let revision: i64 = db
            .query_row("SELECT revision FROM app_state", [], |r| r.get(0))
            .unwrap();
        assert_eq!(revision, 1);
        drop(db);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn market_positions_are_persisted_without_becoming_accounts() {
        let mut db = memory();
        let mut s = state();
        s["market"] = json!({"enabled":false,"autoRefresh":false,"positions":[{"id":"p","symbol":"SPY","name":"ETF","unitsMicros":500000,"costBasisUsdMinor":5000,"quote":null}],"fx":null});
        save(&mut db, s.to_string(), 0).unwrap();
        let count: i64 = db
            .query_row("SELECT count(*) FROM market_positions", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 1);
        let opening: i64 = db
            .query_row("SELECT sum(opening) FROM accounts", [], |r| r.get(0))
            .unwrap();
        assert_eq!(opening, 10000);
    }
    #[test]
    fn provider_quote_refreshes_do_not_duplicate_full_financial_audit() {
        let mut db = memory();
        let mut s = state();
        s["market"] = json!({"enabled":true,"autoRefresh":true,"positions":[{"id":"p","symbol":"SPY","name":"ETF","unitsMicros":500000,"costBasisUsdMinor":5000,"quote":null}],"fx":null});
        save(&mut db, s.to_string(), 0).unwrap();
        s["revision"] = json!(2);
        s["market"]["positions"][0]["quote"] = json!({"symbol":"SPY","priceMicros":123450000,"previousCloseMicros":120000000,"timestamp":1700000000,"receivedAt":"2023-11-14T22:13:20Z","provider":"finnhub"});
        save(&mut db, s.to_string(), 1).unwrap();
        let count: i64 = db
            .query_row("SELECT count(*) FROM audit", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 1);
        s["revision"] = json!(3);
        s["accounts"][0]["name"] = json!("Renamed cash");
        save(&mut db, s.to_string(), 2).unwrap();
        let count: i64 = db
            .query_row("SELECT count(*) FROM audit", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 2);
    }
    #[test]
    fn purchase_records_reconcile_and_persist_without_cash_movements() {
        let mut db = memory();
        let mut s = state();
        let lot = json!({"id":"lot","date":"2026-01-01","entryMode":"amount","priceMicros":500000000,"unitsMicros":2000000,"amountUsdMinor":100000,"feeUsdMinor":100});
        s["market"] = json!({"enabled":false,"autoRefresh":false,"positions":[{"id":"p","symbol":"SPY","name":"ETF","unitsMicros":2000000,"costBasisUsdMinor":100100,"purchases":[lot],"quote":null}],"fx":null});
        save(&mut db, s.to_string(), 0).unwrap();
        let stored: (i64, i64) = db
            .query_row(
                "SELECT amount_usd_minor,units_micros FROM purchase_lots",
                [],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .unwrap();
        assert_eq!(stored, (100000, 2000000));
        assert_eq!(
            db.query_row("SELECT sum(opening) FROM accounts", [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            10000
        );
        assert_eq!(
            db.query_row("SELECT count(*) FROM entries", [], |r| r.get::<_, i64>(0))
                .unwrap(),
            0
        );
        for field in ["costBasisUsdMinor", "unitsMicros"] {
            let mut bad = s.clone();
            bad["revision"] = json!(2);
            bad["market"]["positions"][0][field] = json!(1);
            assert!(save(&mut db, bad.to_string(), 1).is_err());
        }
        let mut bad = s.clone();
        bad["revision"] = json!(2);
        bad["market"]["positions"][0]["purchases"][0]["priceMicros"] = json!(123);
        assert!(save(&mut db, bad.to_string(), 1).is_err());
        assert_eq!(
            db.query_row("SELECT count(*) FROM purchase_lots", [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            1
        );
        s["revision"] = json!(2);
        s["market"]["positions"][0]["purchases"][0]["date"] = json!("2026-01-02");
        save(&mut db, s.to_string(), 1).unwrap();
        assert_eq!(
            db.query_row("SELECT count(*) FROM audit", [], |r| r.get::<_, i64>(0))
                .unwrap(),
            2
        );
    }
    #[test]
    fn migrates_v2_preserving_positions_and_rejects_newer_schema() {
        let path = std::env::temp_dir().join(format!(
            "saldo-v2-{}-{}.db",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap()
        ));
        let key = "12".repeat(32);
        {
            let mut db = open(&path, &key).unwrap();
            let mut s = state();
            s["market"] = json!({"enabled":false,"autoRefresh":false,"positions":[{"id":"p","symbol":"SPY","name":"ETF","unitsMicros":500000,"costBasisUsdMinor":5000,"quote":null}],"fx":null});
            save(&mut db, s.to_string(), 0).unwrap();
            db.execute_batch("DROP TABLE purchase_lots; PRAGMA user_version=2;")
                .unwrap();
        }
        {
            let db = open(&path, &key).unwrap();
            assert_eq!(
                db.query_row("PRAGMA user_version", [], |r| r.get::<_, i64>(0))
                    .unwrap(),
                3
            );
            assert_eq!(
                db.query_row("SELECT units_micros FROM market_positions", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                500000
            );
            assert_eq!(
                db.query_row("SELECT count(*) FROM audit", [], |r| r.get::<_, i64>(0))
                    .unwrap(),
                1
            );
            db.execute_batch("PRAGMA user_version=4;").unwrap();
        }
        assert!(open(&path, &key).is_err());
        std::fs::remove_file(path).unwrap();
    }
}
