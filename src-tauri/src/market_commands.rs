use crate::{err, Store};
use std::{
    sync::{Arc, Mutex},
    time::Instant,
};
#[derive(Default)]
pub struct MarketRuntime(pub Arc<Mutex<Option<Instant>>>);
fn credential() -> Result<keyring::Entry, String> {
    keyring::Entry::new("app.saldo.desktop", "finnhub-api-key")
        .map_err(|_| "OS credential store is unavailable".into())
}
#[tauri::command]
pub async fn market_key_status() -> Result<bool, String> {
    tauri::async_runtime::spawn_blocking(|| match credential()?.get_password() {
        Ok(_) => Ok(true),
        Err(keyring::Error::NoEntry) => Ok(false),
        Err(_) => Err("OS credential store is unavailable".into()),
    })
    .await
    .map_err(|_| "Credential operation failed")?
}
#[tauri::command]
pub async fn set_market_key(api_key: String, consent: bool) -> Result<(), String> {
    if !consent || !saldo_market::valid_key(api_key.trim()) {
        return Err("Explicit consent and a valid Finnhub API key are required".into());
    }
    tauri::async_runtime::spawn_blocking(move || {
        credential()?
            .set_password(api_key.trim())
            .map_err(|_| "Could not save API key in the OS credential store".into())
    })
    .await
    .map_err(|_| "Credential operation failed")?
}
#[tauri::command]
pub async fn clear_market_key() -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(|| match credential()?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(_) => Err("Could not remove the API key from the OS credential store".into()),
    })
    .await
    .map_err(|_| "Credential operation failed")?
}
#[tauri::command]
pub async fn refresh_market_quotes(
    store: tauri::State<'_, Store>,
    runtime: tauri::State<'_, MarketRuntime>,
) -> Result<saldo_market::Batch, String> {
    let json: String = store
        .0
        .lock()
        .map_err(err)?
        .query_row("SELECT json FROM app_state WHERE singleton=1", [], |r| {
            r.get(0)
        })
        .map_err(err)?;
    let state: serde_json::Value =
        serde_json::from_str(&json).map_err(|_| "Invalid market preferences")?;
    if state["market"]["enabled"].as_bool() != Some(true) {
        return Err("Market requests are disabled. Enable the provider explicitly first.".into());
    }
    let symbols: Vec<String> = state["market"]["positions"]
        .as_array()
        .ok_or("Add a watchlist symbol first")?
        .iter()
        .filter_map(|p| p["symbol"].as_str().map(str::to_owned))
        .collect();
    let gate = runtime.0.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut attempt = gate
            .try_lock()
            .map_err(|_| "A market refresh is already running")?;
        if attempt.is_some_and(|t| t.elapsed().as_secs() < 60) {
            return Err("Please wait 60 seconds between provider refreshes".into());
        }
        let key = credential()?
            .get_password()
            .map_err(|_| "Configure your Finnhub API key in Investments first")?;
        *attempt = Some(Instant::now());
        saldo_market::fetch_quotes(&symbols, &key)
    })
    .await
    .map_err(|_| "Market refresh failed")?
}
#[tauri::command]
pub fn open_official_resource(resource: String) -> Result<(), String> {
    let url = if let Some(symbol) = resource.strip_prefix("tradingview:") {
        saldo_market::tradingview_url(symbol)?
    } else {
        match resource.as_str() {
            "finnhub" => "https://finnhub.io/register",
            "GCash" => "https://help.gcash.com/hc/en-us/articles/41329110227737-Are-there-other-ways-to-log-in-to-GCash",
            "Maya" => "https://www.maya.ph/",
            "BPI" => "https://online.bpi.com.ph/",
            "MariBank" => "https://www.maribank.ph/",
            "GoTyme" => "https://www.gotyme.com.ph/help/your-account/opening-a-gotyme-bank-account/downloading-the-app",
            _ => return Err("Unknown official resource".into()),
        }.to_owned()
    };
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("rundll32.exe")
            .args(["url.dll,FileProtocolHandler", &url])
            .spawn()
            .map_err(|_| "Could not open your browser")?;
    }
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg(url)
            .spawn()
            .map_err(|_| "Could not open your browser")?;
    }
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open")
            .arg(url)
            .spawn()
            .map_err(|_| "Could not open your browser")?;
    }
    Ok(())
}
