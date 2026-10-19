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
    for table in ["entries", "goals", "snapshots", "budgets", "accounts"] {
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
    let over:i64=tx.query_row("SELECT count(*) FROM (SELECT g.account_id,sum(g.allocated) AS reserved FROM goals g GROUP BY g.account_id) x JOIN accounts a ON a.id=x.account_id WHERE reserved > max(0,a.opening+coalesce((SELECT sum(CASE WHEN e.account_id=a.id THEN (CASE WHEN e.kind IN ('expense','transfer') THEN -e.amount ELSE e.amount END)-e.fee ELSE 0 END + CASE WHEN e.kind='transfer' AND e.destination_id=a.id THEN e.amount ELSE 0 END) FROM entries e WHERE e.account_id=a.id OR e.destination_id=a.id),0))",[],|r|r.get(0)).map_err(err)?;
    if over > 0 {
        return Err("Goal allocations exceed available funds".into());
    }
    tx.execute(
        "INSERT INTO audit(at,previous_json,new_json) VALUES(datetime('now'),?1,?2)",
        params![previous, json],
    )
    .map_err(err)?;
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
    if version > 1 {
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
}
