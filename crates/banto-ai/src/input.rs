use crate::{Error, Result};

/// Past-only, prepared context. No future target or application-specific DTO.
#[derive(Clone, Debug)]
pub struct ForecastInput {
    batch: usize,
    values: Vec<f32>,
}
impl ForecastInput {
    pub fn new(batch: usize, values: Vec<f32>) -> Result<Self> {
        if !(1..=8).contains(&batch) || values.len() != batch * 3 * 128 {
            return Err(Error::Input("expected finite [B,3,128], B=1..8".into()));
        }
        if values.iter().any(|x| !x.is_finite()) {
            return Err(Error::Input(
                "missing/nonfinite values require an upstream quality policy".into(),
            ));
        }
        Ok(Self { batch, values })
    }
    pub fn batch(&self) -> usize {
        self.batch
    }
    pub fn values(&self) -> &[f32] {
        &self.values
    }
}

/// Quantiles are not an expected-quantity forecast for demand/PSI.
#[derive(Clone, Debug)]
pub struct Forecast {
    pub batch: usize,
    pub quantile_levels: [f32; 3],
    /// Row-major [B,3,32,3], in original signal units.
    pub quantiles: Vec<f32>,
    /// Row-major [B,3,1], diagnostics from the past context.
    pub context_center: Vec<f32>,
    pub context_scale: Vec<f32>,
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn zero_is_a_value_but_missing_and_shape_errors_are_rejected() {
        assert!(ForecastInput::new(1, vec![0.0; 384]).is_ok());
        for batch in [0, 9] {
            assert!(ForecastInput::new(batch, vec![]).is_err());
        }
        assert!(ForecastInput::new(1, vec![0.0; 383]).is_err());
        for bad in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY] {
            let mut x = vec![0.0; 384];
            x[5] = bad;
            assert!(ForecastInput::new(1, x).is_err());
        }
    }
}
