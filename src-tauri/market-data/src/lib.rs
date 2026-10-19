use rust_decimal::{prelude::ToPrimitive, Decimal, RoundingStrategy};
use serde::Serialize;
use serde_json::Value;
use std::{io::Read, str::FromStr, time::Duration};
#[derive(Clone, Serialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct Quote {
    pub symbol: String,
    pub price_micros: i64,
    pub previous_close_micros: Option<i64>,
    pub timestamp: i64,
    pub received_at: String,
    pub provider: &'static str,
}
#[derive(Serialize)]
pub struct QuoteError {
    pub symbol: String,
    pub message: String,
}
#[derive(Serialize)]
pub struct Batch {
    pub quotes: Vec<Quote>,
    pub errors: Vec<QuoteError>,
}
pub fn valid_symbol(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 12
        && s.as_bytes()[0].is_ascii_uppercase()
        && s.bytes()
            .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'.' || b == b'-')
}
pub fn valid_key(key: &str) -> bool {
    (8..=256).contains(&key.len()) && key.bytes().all(|b| b.is_ascii_graphic())
}
fn micros(v: &Value) -> Result<i64, String> {
    let raw = match v {
        Value::Number(n) => n.to_string(),
        _ => return Err("Provider price is missing".into()),
    };
    let decimal = Decimal::from_str(&raw)
        .or_else(|_| Decimal::from_scientific(&raw))
        .map_err(|_| "Invalid provider price")?;
    let n = (decimal.round_dp_with_strategy(6, RoundingStrategy::MidpointAwayFromZero)
        * Decimal::from(1_000_000))
    .to_i64()
    .ok_or("Provider price exceeds precision")?;
    if n <= 0 || n > 1_000_000_000_000 {
        return Err("Provider returned no valid price".into());
    }
    Ok(n)
}
pub fn parse_quote(symbol: &str, body: &str, now: i64) -> Result<Quote, String> {
    if !valid_symbol(symbol) || body.len() > 16384 {
        return Err("Invalid quote response".into());
    }
    let v: Value = serde_json::from_str(body).map_err(|_| "Invalid quote JSON")?;
    if v.get("error").is_some() {
        return Err(
            "Provider rejected the quote request. Check your API key, symbol coverage and plan."
                .into(),
        );
    }
    let timestamp = v["t"]
        .as_i64()
        .ok_or("Provider quote has no market timestamp")?;
    if timestamp <= 0 || timestamp > now + 300 {
        return Err("Provider returned an invalid market timestamp".into());
    }
    Ok(Quote {
        symbol: symbol.into(),
        price_micros: micros(&v["c"])?,
        previous_close_micros: micros(&v["pc"]).ok(),
        timestamp,
        received_at: chrono::DateTime::from_timestamp(now, 0)
            .ok_or("Invalid clock")?
            .to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
        provider: "finnhub",
    })
}
fn request_for(
    client: &reqwest::blocking::Client,
    symbol: &str,
    key: &str,
) -> Result<reqwest::blocking::Request, String> {
    let mut token =
        reqwest::header::HeaderValue::from_str(key).map_err(|_| "Invalid provider credential")?;
    token.set_sensitive(true);
    client
        .get("https://finnhub.io/api/v1/quote")
        .query(&[("symbol", symbol)])
        .header("X-Finnhub-Token", token)
        .build()
        .map_err(|_| "Could not construct provider request".into())
}
fn status_error(status: u16) -> Option<String> {
    match status {
        200 => None,
        401 | 403 => Some(
            "Provider authentication/coverage denied. Check your API key and subscription.".into(),
        ),
        429 => Some("Provider rate limit reached. Wait before refreshing.".into()),
        _ => Some(format!(
            "Market provider returned HTTP {status}. Cached prices retained."
        )),
    }
}
pub fn fetch_quotes(symbols: &[String], key: &str) -> Result<Batch, String> {
    if symbols.is_empty() || symbols.len() > 10 || symbols.iter().any(|s| !valid_symbol(s)) {
        return Err("Choose 1–10 valid US tickers".into());
    }
    if !valid_key(key) {
        return Err("Configure a valid Finnhub API key".into());
    }
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(8))
        .redirect(reqwest::redirect::Policy::none())
        .https_only(true)
        .user_agent("SALDO/0.2.0")
        .build()
        .map_err(|_| "Could not initialize secure market connection")?;
    let mut batch = Batch {
        quotes: vec![],
        errors: vec![],
    };
    for symbol in symbols {
        let result = (|| {
            let response = client
                .execute(request_for(&client, symbol, key)?)
                .map_err(|_| {
                    "Market provider could not be reached. Cached prices have been retained."
                        .to_string()
                })?;
            if let Some(message) = status_error(response.status().as_u16()) {
                return Err(message);
            }
            let mut body = String::new();
            response
                .take(16385)
                .read_to_string(&mut body)
                .map_err(|_| "Could not read provider response")?;
            parse_quote(symbol, &body, chrono::Utc::now().timestamp())
        })();
        match result {
            Ok(q) => batch.quotes.push(q),
            Err(message) => {
                let stop = message.contains("authentication") || message.contains("rate limit");
                batch.errors.push(QuoteError {
                    symbol: symbol.clone(),
                    message,
                });
                if stop {
                    break;
                }
            }
        }
    }
    Ok(batch)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parses_exact_microprices_and_market_time() {
        let q = parse_quote(
            "SPY",
            r#"{"c":612.1234564,"pc":610.5,"t":1700000000}"#,
            1700000010,
        )
        .unwrap();
        assert_eq!(q.price_micros, 612123456);
        assert_eq!(q.previous_close_micros, Some(610500000));
        assert_eq!(q.timestamp, 1700000000);
    }
    #[test]
    fn missing_zero_and_error_prices_are_not_live_quotes() {
        for s in [
            r#"{"c":0,"t":1700000000}"#,
            r#"{"c":100}"#,
            r#"{"error":"token=secret"}"#,
            r#"{"c":-100,"t":1700000000}"#,
        ] {
            let error = parse_quote("SPY", s, 1700000010).unwrap_err();
            assert!(!error.contains("secret"));
        }
    }
    #[test]
    fn rejects_symbols_and_future_times() {
        assert!(!valid_symbol("SPY&token=x"));
        assert!(!valid_symbol("^GSPC"));
        assert!(valid_symbol("BRK.B"));
        assert!(parse_quote("SPY", r#"{"c":100,"t":1700001000}"#, 1700000000).is_err());
    }
    #[test]
    fn preserves_old_quotes_for_explicit_staleness() {
        let q = parse_quote("VOO", r#"{"c":100,"pc":99,"t":1700000000}"#, 1701000000).unwrap();
        assert_eq!(q.timestamp, 1700000000);
    }
    #[test]
    fn auth_key_and_response_size_bounds() {
        assert!(!valid_key("secret\nkey"));
        assert!(!valid_key(""));
        assert!(parse_quote("SPY", &"x".repeat(16385), 1700000000).is_err());
    }
    #[test]
    fn authentication_is_sensitive_and_never_in_the_request_url() {
        let client = reqwest::blocking::Client::new();
        let request = request_for(&client, "SPY", "test-key-123456").unwrap();
        assert_eq!(
            request.url().as_str(),
            "https://finnhub.io/api/v1/quote?symbol=SPY"
        );
        let header = request.headers().get("X-Finnhub-Token").unwrap();
        assert!(header.is_sensitive());
        assert_eq!(header.to_str().unwrap(), "test-key-123456");
        assert!(!format!("{request:?}").contains("test-key-123456"));
    }
    #[test]
    fn provider_errors_explain_auth_limits_and_outages() {
        assert!(status_error(200).is_none());
        assert!(status_error(401).unwrap().contains("authentication"));
        assert!(status_error(403).unwrap().contains("coverage"));
        assert!(status_error(429).unwrap().contains("rate limit"));
        assert!(status_error(500).unwrap().contains("500"));
    }
}
