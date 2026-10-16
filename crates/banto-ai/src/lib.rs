//! Portable AI implementation owned by banto-ai, independent of application DTOs.
//! R1 implements fixed SmallForecaster inference. Training is a later R2 gate.

pub mod checkpoint;
#[cfg(feature = "reference-normalization")]
pub mod context;
pub mod error;
#[cfg(feature = "fma-extension")]
pub mod fma;
#[cfg(feature = "fused-linear-extension")]
pub mod fused_linear;
pub mod input;
pub mod model;
pub use error::{Error, Result};
pub use input::{Forecast, ForecastInput};
pub use model::SmallForecaster;
