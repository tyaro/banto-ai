//! Portable AI implementation owned by banto-ai, independent of application DTOs.
//! R1 implements fixed SmallForecaster inference. Training is a later R2 gate;
//! `training` holds the R2P artificial loss, clip and AdamW parts.

pub mod checkpoint;
pub mod error;
pub mod input;
pub mod model;
pub mod synthetic_checkpoint;
pub mod training;
pub use error::{Error, Result};
pub use input::{Forecast, ForecastInput};
pub use model::SmallForecaster;
