use std::fmt;

#[derive(Debug)]
pub enum Error {
    Input(String),
    Model(String),
    Integrity(String),
    Backend(String),
    Io(std::io::Error),
    Json(serde_json::Error),
}
pub type Result<T> = std::result::Result<T, Error>;
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Input(s) => write!(f, "invalid input: {s}"),
            Self::Model(s) => write!(f, "invalid model: {s}"),
            Self::Integrity(s) => write!(f, "integrity check: {s}"),
            Self::Backend(s) => write!(f, "backend: {s}"),
            Self::Io(e) => write!(f, "{e}"),
            Self::Json(e) => write!(f, "{e}"),
        }
    }
}
impl std::error::Error for Error {}
impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Self::Io(e)
    }
}
impl From<serde_json::Error> for Error {
    fn from(e: serde_json::Error) -> Self {
        Self::Json(e)
    }
}
