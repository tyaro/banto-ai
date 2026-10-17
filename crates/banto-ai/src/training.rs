//! R2P artificial training parts on explicit Flex CPU float32: normalized
//! pinball loss, ordered named gradients, global-norm clip and an AdamW that
//! follows the single-tensor Torch update (foreach/fused off).
//!
//! These parts are verified only against the fixed artificial R2P reference.
//! They do not make SmallForecaster trainable and do not satisfy R1 or R2.

use crate::{Error, Result};
use burn::tensor::{Device, Tensor, TensorData};
use std::collections::BTreeSet;

/// Quantile levels of the three prediction heads, in output order.
pub const QUANTILES: [f32; 3] = [0.1, 0.5, 0.9];

pub fn read<const D: usize>(x: &Tensor<D>) -> Result<Vec<f32>> {
    x.to_data()
        .try_to_vec::<f32>()
        .map_err(|e| Error::Backend(format!("{e:?}")))
}
fn finite(name: &str, values: &[f32]) -> Result<()> {
    match values.iter().all(|v| v.is_finite()) {
        true => Ok(()),
        false => Err(Error::Input(format!("nonfinite {name}"))),
    }
}

/// Host-validated loss inputs: prediction [B,C,H,3], target [B,C,H] and the
/// constant per-channel center/scale [B,C]. Zero is a valid value.
#[derive(Clone, Debug)]
pub struct LossInput {
    pub dims: [usize; 3],
    pub prediction: Vec<f32>,
    pub actual: Vec<f32>,
    pub center: Vec<f32>,
    pub scale: Vec<f32>,
}
impl LossInput {
    pub fn new(
        prediction_shape: [usize; 4],
        prediction: Vec<f32>,
        actual_shape: [usize; 3],
        actual: Vec<f32>,
        center: Vec<f32>,
        scale: Vec<f32>,
    ) -> Result<Self> {
        let [b, c, h, q] = prediction_shape;
        if q != QUANTILES.len() || actual_shape != [b, c, h] {
            return Err(Error::Input(format!(
                "prediction {prediction_shape:?} and target {actual_shape:?} do not align"
            )));
        }
        let counts = [
            (prediction.len(), b * c * h * q),
            (actual.len(), b * c * h),
            (center.len(), b * c),
            (scale.len(), b * c),
        ];
        if b * c * h == 0 || counts.iter().any(|(got, want)| got != want) {
            return Err(Error::Input(
                "loss tensor lengths do not match shapes".into(),
            ));
        }
        for (name, values) in [
            ("prediction", &prediction),
            ("target", &actual),
            ("center", &center),
            ("scale", &scale),
        ] {
            finite(name, values)?;
        }
        if scale.iter().any(|s| *s <= 0.0) {
            return Err(Error::Input("scale must be positive".into()));
        }
        Ok(Self {
            dims: [b, c, h],
            prediction,
            actual,
            center,
            scale,
        })
    }
    pub fn prediction(&self, device: &Device) -> Tensor<4> {
        let [b, c, h] = self.dims;
        Tensor::from_data(
            TensorData::new(self.prediction.clone(), [b, c, h, QUANTILES.len()]),
            device,
        )
    }
    pub fn loss(&self, prediction: Tensor<4>) -> Result<Tensor<1>> {
        let [b, c, h] = self.dims;
        if prediction.dims() != [b, c, h, QUANTILES.len()] {
            return Err(Error::Input(
                "prediction tensor does not match the loss input".into(),
            ));
        }
        let device = prediction.device();
        let actual = Tensor::from_data(TensorData::new(self.actual.clone(), [b, c, h]), &device);
        let center = Tensor::from_data(TensorData::new(self.center.clone(), [b, c, 1]), &device);
        let scale = Tensor::from_data(TensorData::new(self.scale.clone(), [b, c, 1]), &device);
        Ok(pinball_loss(prediction, actual, center, scale))
    }
}

/// Mean over B*C*H*3 of max(tau*r, (tau-1)*r) with r=(actual-center)/scale-prediction.
/// Written as (tau-1/2)*r+|r|/2, the same value, so that an exact tie r=0 takes
/// the subgradient (1/2-tau)/N of Torch's maximum instead of one side.
pub fn pinball_loss(
    prediction: Tensor<4>,
    actual: Tensor<3>,
    center: Tensor<3>,
    scale: Tensor<3>,
) -> Tensor<1> {
    let device = prediction.device();
    let half_offset = Tensor::<1>::from_data(
        TensorData::new(QUANTILES.map(|t| t - 0.5).to_vec(), [QUANTILES.len()]),
        &device,
    )
    .reshape([1, 1, 1, QUANTILES.len()]);
    let r = ((actual - center) / scale).unsqueeze_dim::<4>(3) - prediction;
    (r.clone() * half_offset + r.abs() * 0.5).mean()
}

/// A trainable tensor identified by name; values are stored flat with their shape.
#[derive(Clone, Debug)]
pub struct Parameter {
    pub name: String,
    pub shape: Vec<usize>,
    pub value: Tensor<1>,
}
impl Parameter {
    pub fn new(name: &str, shape: Vec<usize>, values: Vec<f32>, device: &Device) -> Result<Self> {
        if values.len() != shape.iter().product::<usize>() || values.is_empty() {
            return Err(Error::Input(format!(
                "{name} values do not match {shape:?}"
            )));
        }
        finite(name, &values)?;
        let len = values.len();
        Ok(Self {
            name: name.into(),
            shape,
            value: Tensor::from_data(TensorData::new(values, [len]), device),
        })
    }
    fn len(&self) -> usize {
        self.shape.iter().product()
    }
}

/// Orders explicitly named gradients like `parameters`. Duplicate or unknown
/// names are rejected before any lookup, and a missing gradient is an error,
/// never an implicit zero.
pub fn ordered_gradients(
    parameters: &[Parameter],
    named: Vec<(String, Tensor<1>)>,
) -> Result<Vec<Tensor<1>>> {
    let mut seen = BTreeSet::new();
    for (name, _) in &named {
        if !seen.insert(name.as_str()) {
            return Err(Error::Input(format!("duplicate gradient {name}")));
        }
        if !parameters.iter().any(|p| &p.name == name) {
            return Err(Error::Input(format!("unknown gradient {name}")));
        }
    }
    let mut named = named;
    let mut ordered = Vec::with_capacity(parameters.len());
    for p in parameters {
        let at = named
            .iter()
            .position(|(name, _)| name == &p.name)
            .ok_or_else(|| Error::Input(format!("missing gradient {}", p.name)))?;
        let (_, g) = named.swap_remove(at);
        if g.dims() != [p.len()] {
            return Err(Error::Input(format!("gradient {} has wrong shape", p.name)));
        }
        ordered.push(g);
    }
    Ok(ordered)
}

pub struct Clipped {
    pub norm: Tensor<1>,
    pub coefficient: Tensor<1>,
    pub gradients: Vec<Tensor<1>>,
}

/// Global L2 norm over all gradients (the norm of per-tensor norms, as Torch
/// computes it) and one coefficient min(1, max_norm/(norm+1e-6)) for all.
pub fn clip_global_norm(gradients: Vec<Tensor<1>>, max_norm: f32) -> Result<Clipped> {
    if gradients.is_empty() {
        return Err(Error::Input("no gradients to clip".into()));
    }
    if !(max_norm.is_finite() && max_norm > 0.0) {
        return Err(Error::Input("max_norm must be positive and finite".into()));
    }
    let per: Vec<Tensor<1>> = gradients
        .iter()
        .map(|g| (g.clone() * g.clone()).sum().sqrt())
        .collect();
    let per = Tensor::cat(per, 0);
    let norm = (per.clone() * per).sum().sqrt();
    finite("gradient norm", &read(&norm)?)?;
    let coefficient = (norm.clone() + 1e-6)
        .recip()
        .mul_scalar(max_norm)
        .clamp_max(1.0);
    let gradients = gradients
        .into_iter()
        .map(|g| g * coefficient.clone())
        .collect();
    Ok(Clipped {
        norm,
        coefficient,
        gradients,
    })
}

#[derive(Clone, Copy, Debug)]
pub struct AdamW {
    pub lr: f64,
    pub betas: (f64, f64),
    pub eps: f64,
    pub weight_decay: f64,
}

/// Moments per parameter in parameter order and an integer step counter.
#[derive(Clone, Debug)]
pub struct AdamWState {
    pub step: u64,
    pub m: Vec<Tensor<1>>,
    pub v: Vec<Tensor<1>>,
}
impl AdamWState {
    pub fn zeros(parameters: &[Parameter]) -> Self {
        let zeros = |p: &Parameter| Tensor::zeros([p.len()], &p.value.device());
        Self {
            step: 0,
            m: parameters.iter().map(zeros).collect(),
            v: parameters.iter().map(zeros).collect(),
        }
    }
}

impl AdamW {
    /// One update of every parameter, including those with zero gradients:
    /// decoupled decay, lerp first moment, addcmul second moment, then
    /// addcdiv with bias corrections from the incremented integer step.
    pub fn step(
        &self,
        parameters: &mut [Parameter],
        gradients: &[Tensor<1>],
        state: &mut AdamWState,
    ) -> Result<()> {
        let n = parameters.len();
        if gradients.len() != n || state.m.len() != n || state.v.len() != n {
            return Err(Error::Input(
                "optimizer state does not match parameters".into(),
            ));
        }
        for (i, p) in parameters.iter().enumerate() {
            let dims = [p.len()];
            if gradients[i].dims() != dims || state.m[i].dims() != dims || state.v[i].dims() != dims
            {
                return Err(Error::Input(format!("{} optimizer shapes differ", p.name)));
            }
        }
        let (b1, b2) = self.betas;
        state.step += 1;
        let t = state.step as f64;
        let decay = (1.0 - self.lr * self.weight_decay) as f32;
        let step_size = (self.lr / (1.0 - b1.powf(t))) as f32;
        let correction2 = (1.0 - b2.powf(t)).sqrt() as f32;
        for (i, p) in parameters.iter_mut().enumerate() {
            let g = gradients[i].clone();
            let m = state.m[i].clone();
            let m = m.clone() + (g.clone() - m) * ((1.0 - b1) as f32);
            let v = state.v[i].clone() * (b2 as f32) + g.clone().mul_scalar((1.0 - b2) as f32) * g;
            let denom = v
                .clone()
                .sqrt()
                .div_scalar(correction2)
                .add_scalar(self.eps as f32);
            p.value = p.value.clone() * decay + m.clone().mul_scalar(-step_size) / denom;
            state.m[i] = m;
            state.v[i] = v;
        }
        Ok(())
    }
}

/// Host values of one parameter, for checkpoints and comparisons.
pub fn values(parameter: &Parameter) -> Result<Vec<f32>> {
    read(&parameter.value)
}

/// What one update saw: the loss on fresh leaves and the gradients before and
/// after the global clip, in parameter order.
pub struct StepRecord {
    pub loss: Tensor<1>,
    pub raw_gradients: Vec<Tensor<1>>,
    pub clipped: Clipped,
}

/// Loss and named gradients without an update. Every parameter becomes a
/// fresh autodiff leaf, so no graph survives the call; `loss` maps the leaves
/// (in parameter order) to a scalar. A missing or nonfinite gradient is an error.
pub fn loss_and_gradients(
    parameters: &[Parameter],
    loss: impl FnOnce(&[Tensor<1>]) -> Result<Tensor<1>>,
) -> Result<(Tensor<1>, Vec<Tensor<1>>)> {
    let leaves: Vec<Tensor<1>> = parameters
        .iter()
        .map(|p| p.value.clone().autodiff().require_grad())
        .collect();
    let value = loss(&leaves)?;
    finite("loss", &read(&value)?)?;
    let grads = value.backward();
    let named = parameters
        .iter()
        .zip(&leaves)
        .filter_map(|(p, leaf)| leaf.grad(&grads).map(|g| (p.name.clone(), g)))
        .collect();
    let gradients = ordered_gradients(parameters, named)?;
    for (p, g) in parameters.iter().zip(&gradients) {
        finite(&format!("{} gradient", p.name), &read(g)?)?;
    }
    Ok((value.without_autodiff(), gradients))
}

/// One training update: loss and gradients on fresh leaves, global clip, then
/// AdamW on the plain (non-autodiff) parameter values.
pub fn train_step(
    parameters: &mut [Parameter],
    state: &mut AdamWState,
    optimizer: &AdamW,
    max_norm: f32,
    loss: impl FnOnce(&[Tensor<1>]) -> Tensor<1>,
) -> Result<StepRecord> {
    let (loss, raw_gradients) = loss_and_gradients(parameters, |leaves| Ok(loss(leaves)))?;
    let clipped = clip_global_norm(raw_gradients.clone(), max_norm)?;
    optimizer.step(parameters, &clipped.gradients, state)?;
    Ok(StepRecord {
        loss,
        raw_gradients,
        clipped,
    })
}
