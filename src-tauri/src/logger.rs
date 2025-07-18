use log::{Log, Metadata, Record, Level};
use regex::Regex;
use std::sync::OnceLock;

static SANITIZER: OnceLock<SecretSanitizer> = OnceLock::new();

pub struct SecretSanitizer {
    patterns: Vec<Regex>,
}

impl SecretSanitizer {
    pub fn new() -> Self {
        Self {
            patterns: vec![
                // API keys and tokens
                Regex::new(r"(?i)(api[_-]?key|token|secret|password|auth|bearer)\s*[:=]\s*['\"]?([^'\";\s]+)").unwrap(),
                // Base64 encoded secrets (longer than 20 chars)
                Regex::new(r"[A-Za-z0-9+/]{20,}={0,2}").unwrap(),
                // UUIDs
                Regex::new(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}").unwrap(),
                // JWT tokens
                Regex::new(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+").unwrap(),
                // Common secret patterns
                Regex::new(r"(?i)(private[_-]?key|client[_-]?secret|access[_-]?token)\s*[:=]\s*['\"]?([^'\";\s]+)").unwrap(),
                // Command arguments that might contain secrets
                Regex::new(r"--password[= ][^ ]+").unwrap(),
                Regex::new(r"--token[= ][^ ]+").unwrap(),
                Regex::new(r"--secret[= ][^ ]+").unwrap(),
                // File paths that might contain user info
                Regex::new(r"/Users/[^/]+/").unwrap(),
                Regex::new(r"/home/[^/]+/").unwrap(),
                Regex::new(r"C:\\Users\\[^\\]+\\").unwrap(),
            ],
        }
    }
    
    pub fn sanitize(&self, text: &str) -> String {
        let mut result = text.to_string();
        
        for pattern in &self.patterns {
            result = pattern.replace_all(&result, |caps: &regex::Captures| {
                if caps.len() > 2 {
                    // Keep the key part, redact the value
                    format!("{}=<REDACTED>", &caps[1])
                } else if result.contains("/Users/") || result.contains("/home/") || result.contains("C:\\Users\\") {
                    // For file paths, keep structure but redact username
                    caps[0].replace(
                        &caps[0]
                            .split('/')
                            .nth(2)
                            .unwrap_or("")
                            .to_string(),
                        "<USER>"
                    )
                } else {
                    // Fully redact other patterns
                    "<REDACTED>".to_string()
                }
            }).to_string();
        }
        
        result
    }
}

pub struct SanitizingLogger {
    inner: env_logger::Logger,
}

impl SanitizingLogger {
    pub fn new() -> Self {
        SANITIZER.set(SecretSanitizer::new()).ok();
        
        Self {
            inner: env_logger::Builder::from_default_env()
                .format_timestamp_millis()
                .build()
                .into(),
        }
    }
}

impl Log for SanitizingLogger {
    fn enabled(&self, metadata: &Metadata) -> bool {
        self.inner.enabled(metadata)
    }
    
    fn log(&self, record: &Record) {
        if self.enabled(record.metadata()) {
            let sanitizer = SANITIZER.get().unwrap();
            let sanitized_message = sanitizer.sanitize(&format!("{}", record.args()));
            
            // Create a new record with sanitized message
            log::logger().log(
                &Record::builder()
                    .args(format_args!("{}", sanitized_message))
                    .level(record.level())
                    .target(record.target())
                    .module_path(record.module_path())
                    .file(record.file())
                    .line(record.line())
                    .build(),
            );
        }
    }
    
    fn flush(&self) {
        self.inner.flush()
    }
}

pub fn init_sanitizing_logger() {
    log::set_boxed_logger(Box::new(SanitizingLogger::new()))
        .map(|()| log::set_max_level(log::LevelFilter::Info))
        .expect("Failed to initialize sanitizing logger");
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_sanitize_api_keys() {
        let sanitizer = SecretSanitizer::new();
        
        assert_eq!(
            sanitizer.sanitize("api_key: sk-1234567890abcdef"),
            "api_key=<REDACTED>"
        );
        
        assert_eq!(
            sanitizer.sanitize("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"),
            "Bearer <REDACTED>"
        );
    }
    
    #[test]
    fn test_sanitize_file_paths() {
        let sanitizer = SecretSanitizer::new();
        
        assert_eq!(
            sanitizer.sanitize("/Users/johndoe/.vibesafe/config.json"),
            "/Users/<USER>/.vibesafe/config.json"
        );
        
        assert_eq!(
            sanitizer.sanitize("/home/janedoe/.config/vibesafe/"),
            "/home/<USER>/.config/vibesafe/"
        );
    }
    
    #[test]
    fn test_sanitize_command_args() {
        let sanitizer = SecretSanitizer::new();
        
        assert_eq!(
            sanitizer.sanitize("vibesafe add MY_SECRET --password=supersecret123"),
            "vibesafe add MY_SECRET <REDACTED>"
        );
    }
}