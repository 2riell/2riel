#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod market_commands;
use market_commands::*;
use rand::RngCore;
use rusqlite::Connection;
fn err(e: impl std::fmt::Display) -> String {
    e.to_string()
}
use std::sync::Mutex;
use tauri::Manager;
struct Store(Mutex<Connection>);
fn open(app: &tauri::App) -> Result<Connection, String> {
    let dir = app.path().app_data_dir().map_err(err)?;
    std::fs::create_dir_all(&dir).map_err(err)?;
    let path = dir.join("saldo.db");
    let credential = keyring::Entry::new("app.saldo.desktop", "database-key").map_err(err)?;
    let key = match credential.get_password() {
        Ok(k) => k,
        Err(keyring::Error::NoEntry) => {
            if path.exists() {
                return Err("Database key missing. Restore your OS keychain; do not create a replacement key.".into());
            }
            let mut bytes = [0u8; 32];
            rand::rngs::OsRng.fill_bytes(&mut bytes);
            let k = hex::encode(bytes);
            credential.set_password(&k).map_err(err)?;
            k
        }
        Err(e) => return Err(err(e)),
    };
    if key.len() != 64 || !key.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("Invalid stored encryption key".into());
    }
    saldo_core::open(path, &key)
}
#[tauri::command]
fn load_state(store: tauri::State<Store>) -> Result<String, String> {
    store
        .0
        .lock()
        .map_err(err)?
        .query_row("SELECT json FROM app_state WHERE singleton=1", [], |r| {
            r.get(0)
        })
        .map_err(err)
}
#[tauri::command]
fn save_state(
    store: tauri::State<Store>,
    json: String,
    expected_revision: i64,
) -> Result<(), String> {
    let mut db = store.0.lock().map_err(err)?;
    saldo_core::save(&mut db, json, expected_revision)
}
fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let db = open(app).map_err(std::io::Error::other)?;
            app.manage(Store(Mutex::new(db)));
            app.manage(MarketRuntime::default());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            load_state,
            save_state,
            market_key_status,
            set_market_key,
            clear_market_key,
            refresh_market_quotes,
            open_official_resource
        ])
        .run(tauri::generate_context!())
        .expect("SALDO startup failed; encrypted storage unavailable");
}
