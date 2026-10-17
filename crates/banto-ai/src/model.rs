//! Full SmallForecaster on explicit Flex CPU; application types stay outside.

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn temporal_query_cannot_change_past_outputs() {
        let mut state = BTreeMap::new();
        for (name, shape) in crate::checkpoint::expected_shapes() {
            state.insert(name, vec![0.0; shape.iter().product()]);
        }
        for layer in ["q", "k", "v", "out"] {
            let key = format!("blocks.0.temporal.{layer}.weight");
            for i in 0..64 {
                state.get_mut(&key).unwrap()[i * 64 + i] = 1.0;
            }
        }
        let model = SmallForecaster::from_neutral(NeutralModel { tensors: state });
        let baseline = Tensor::<3>::zeros([1, 5, 64], &model.device);
        let mut changed = vec![0.0; 5 * 64];
        changed[4 * 64..].fill(9.0);
        let changed = Tensor::<3>::from_data(TensorData::new(changed, [1, 5, 64]), &model.device);
        let a = read(&model.attention(baseline, "blocks.0.temporal", true)).unwrap();
        let b = read(&model.attention(changed, "blocks.0.temporal", true)).unwrap();
        assert_eq!(&a[..4 * 64], &b[..4 * 64]);
        assert_ne!(&a[4 * 64..], &b[4 * 64..]);
    }
}

use crate::{
    Error, Result,
    checkpoint::NeutralModel,
    input::{Forecast, ForecastInput},
};
use burn::tensor::{Bool, Device, Tensor, TensorData, activation};
use serde::Serialize;
use std::collections::BTreeMap;
#[derive(Clone, Debug, Serialize)]
pub struct TraceTensor {
    pub name: String,
    pub shape: Vec<usize>,
    pub values: Vec<f32>,
}
pub struct SmallForecaster {
    device: Device,
    state: BTreeMap<String, Tensor<1>>,
}
/// Tensor outputs of one forward pass; `normalized` is what the training loss uses.
pub struct ForwardTensors {
    pub normalized: Tensor<4>,
    pub physical: Tensor<4>,
    pub center: Tensor<3>,
    pub scale: Tensor<3>,
}
fn read<const D: usize>(x: &Tensor<D>) -> Result<Vec<f32>> {
    x.to_data()
        .to_vec::<f32>()
        .map_err(|e| Error::Backend(format!("{e:?}")))
}
fn capture<const D: usize>(
    t: &mut Option<Vec<TraceTensor>>,
    name: &str,
    x: &Tensor<D>,
) -> Result<()> {
    if let Some(items) = t {
        let values = read(x)?;
        if values.iter().any(|v| !v.is_finite()) {
            return Err(Error::Backend(format!("nonfinite {name}")));
        }
        items.push(TraceTensor {
            name: name.into(),
            shape: x.dims().to_vec(),
            values,
        });
    }
    Ok(())
}
fn gelu<const D: usize>(x: Tensor<D>) -> Tensor<D> {
    x.clone() * 0.5 * ((x / std::f32::consts::SQRT_2).erf() + 1.0)
}
fn softplus<const D: usize>(x: Tensor<D>) -> Tensor<D> {
    let high = x.clone().greater_elem(20.0);
    x.clone().clamp_max(20.0).exp().log1p().mask_where(high, x)
}
/// Balanced f32 reduction for the fixed power-of-two context and norm widths.
/// Avoid the serial summation error of the scalar Flex sum kernel while keeping
/// the computation in tensor operations for the later training implementation.
fn mean_last<const D: usize>(x: Tensor<D>) -> Tensor<D> {
    let mut shape = x.dims();
    let width = shape[D - 1];
    assert!(width.is_power_of_two());
    let rows = shape.iter().product::<usize>() / width;
    let mut count = width;
    let mut reduced = x.reshape([rows, width]);
    while count > 1 {
        reduced = reduced
            .reshape([rows, count / 2, 2])
            .sum_dim(2)
            .reshape([rows, count / 2]);
        count /= 2;
    }
    shape[D - 1] = 1;
    (reduced / width as f32).reshape(shape)
}
impl SmallForecaster {
    pub fn from_neutral(m: NeutralModel) -> Self {
        let device = Device::flex();
        let state = m
            .tensors
            .into_iter()
            .map(|(name, v)| {
                let n = v.len();
                (
                    name,
                    Tensor::<1>::from_data(TensorData::new(v, [n]), &device),
                )
            })
            .collect();
        Self { device, state }
    }
    /// Builds the model from flat named tensors, e.g. autodiff leaves for
    /// training. Names and lengths must match `checkpoint::expected_shapes()`,
    /// and all tensors must share one device, which the model then uses (without
    /// autodiff) for its own constants such as the causal mask.
    pub fn from_named(state: BTreeMap<String, Tensor<1>>) -> Result<Self> {
        let expected = crate::checkpoint::expected_shapes();
        if state.len() != expected.len() {
            return Err(Error::Model(
                "model tensor set differs from the expected names".into(),
            ));
        }
        let device = state
            .get("horizon")
            .ok_or_else(|| Error::Model("missing tensor horizon".into()))?
            .device()
            .without_autodiff();
        for (name, shape) in &expected {
            let t = state
                .get(name)
                .ok_or_else(|| Error::Model(format!("missing tensor {name}")))?;
            if t.dims() != [shape.iter().product::<usize>()] {
                return Err(Error::Model(format!("{name} has the wrong length")));
            }
            if t.device() != device {
                return Err(Error::Model(format!("{name} is on a different device")));
            }
        }
        Ok(Self { device, state })
    }
    fn p<const D: usize>(&self, name: &str, shape: [usize; D]) -> Tensor<D> {
        self.state[name].clone().reshape(shape)
    }
    fn linear<const D: usize>(&self, x: Tensor<D>, name: &str, out: usize) -> Tensor<D> {
        let mut shape = x.dims();
        let input = shape[D - 1];
        let rows = shape.iter().product::<usize>() / input;
        let w = self.p(&format!("{name}.weight"), [out, input]).transpose();
        let bias = self.p(&format!("{name}.bias"), [1, out]);
        shape[D - 1] = out;
        (x.reshape([rows, input]).matmul(w) + bias).reshape(shape)
    }
    fn norm<const D: usize>(&self, x: Tensor<D>, name: &str) -> Tensor<D> {
        let mu = mean_last(x.clone());
        let centered = x - mu;
        let var = mean_last(centered.clone().square());
        let mut shape = [1; D];
        shape[D - 1] = 64;
        // Match the reference CPU LayerNorm's row inverse-std multiplication.
        centered * (var + 1e-5).sqrt().recip() * self.p(&format!("{name}.weight"), shape)
            + self.p(&format!("{name}.bias"), shape)
    }
    fn attention(&self, x: Tensor<3>, name: &str, causal: bool) -> Tensor<3> {
        let [b, n, _] = x.dims();
        let project = |layer: &str| {
            self.linear(x.clone(), &format!("{name}.{layer}"), 64)
                .reshape([b, n, 4, 16])
                .swap_dims(1, 2)
        };
        let q = project("q");
        let k = project("k");
        let v = project("v");
        let mut logits = q.matmul(k.swap_dims(2, 3)) / 4.0;
        if causal {
            let mask: Vec<bool> = (0..n * n).map(|i| i % n > i / n).collect();
            logits = logits.mask_fill(
                Tensor::<4, Bool>::from_data(TensorData::new(mask, [1, 1, n, n]), &self.device),
                f32::NEG_INFINITY,
            );
        }
        let mixed = activation::softmax(logits, 3)
            .matmul(v)
            .swap_dims(1, 2)
            .reshape([b, n, 64]);
        self.linear(mixed, &format!("{name}.out"), 64)
    }
    pub fn predict(&self, input: &ForecastInput) -> Result<Forecast> {
        self.run(input, false).map(|(f, _)| f)
    }
    /// Diagnostic snapshots for the finite parity harness.
    pub fn predict_traced(&self, input: &ForecastInput) -> Result<(Forecast, Vec<TraceTensor>)> {
        self.run(input, true)
    }
    /// The forward pass shared by inference and training: context [B,3,128] to
    /// normalized and physical quantiles plus the context center and scale, all
    /// as tensors so a training loss can use them without host readback.
    pub fn forward(&self, context: Tensor<3>) -> Result<ForwardTensors> {
        self.forward_inner(context, &mut None)
    }
    fn forward_inner(
        &self,
        x: Tensor<3>,
        trace: &mut Option<Vec<TraceTensor>>,
    ) -> Result<ForwardTensors> {
        let [b, channels, width] = x.dims();
        if channels != 3 || width != 128 || b == 0 {
            return Err(Error::Input("context must be [batch,3,128]".into()));
        }
        let mu = mean_last(x.clone());
        let centered = x - mu.clone();
        let scale = mean_last(centered.clone().square())
            .sqrt()
            .max_pair(self.p("scale_floor", [1, 3, 1]));
        let normalized = centered / scale.clone();
        capture(trace, "context_center", &mu)?;
        capture(trace, "context_scale", &scale)?;
        capture(trace, "normalized_context", &normalized)?;
        let patch = self.linear(normalized.reshape([b, 3, 4, 32]), "patch", 64);
        capture(trace, "patch", &patch)?;
        let query = self.p("horizon", [1, 1, 1, 64]).expand([b, 3, 1, 64]);
        let mut tokens = Tensor::cat(vec![patch, query], 2) + self.p("position", [1, 1, 5, 64]);
        capture(trace, "tokens", &tokens)?;
        for i in 0..2 {
            let key = format!("blocks.{i}");
            let z = self.norm(tokens.clone(), &format!("{key}.norms.0"));
            capture(trace, &format!("{key}.norms.0"), &z)?;
            let t = self.attention(z.reshape([b * 3, 5, 64]), &format!("{key}.temporal"), true);
            capture(trace, &format!("{key}.temporal"), &t)?;
            tokens = tokens + t.reshape([b, 3, 5, 64]);
            let z = self.norm(tokens.clone(), &format!("{key}.norms.1"));
            capture(trace, &format!("{key}.norms.1"), &z)?;
            let v = self.attention(
                z.swap_dims(1, 2).reshape([b * 5, 3, 64]),
                &format!("{key}.variate"),
                false,
            );
            capture(trace, &format!("{key}.variate"), &v)?;
            tokens = tokens + v.reshape([b, 5, 3, 64]).swap_dims(1, 2);
            let z = self.norm(tokens.clone(), &format!("{key}.norms.2"));
            capture(trace, &format!("{key}.norms.2"), &z)?;
            let hidden = gelu(self.linear(z, &format!("{key}.ff.0"), 128));
            capture(trace, &format!("{key}.ff.1"), &hidden)?;
            tokens = tokens + self.linear(hidden, &format!("{key}.ff.2"), 64);
            capture(trace, &key, &tokens)?;
        }
        let last = tokens.slice([0..b, 0..3, 4..5, 0..64]).reshape([b, 3, 64]);
        let last = self.norm(last, "final_norm");
        capture(trace, "final_norm", &last)?;
        let head = self.linear(last, "head", 96);
        capture(trace, "head", &head)?;
        let raw = head.reshape([b, 3, 32, 3]);
        let mid: Tensor<3> = raw.clone().slice([0..b, 0..3, 0..32, 0..1]).squeeze_dim(3);
        let low: Tensor<3> = raw.clone().slice([0..b, 0..3, 0..32, 1..2]).squeeze_dim(3);
        let high: Tensor<3> = raw.slice([0..b, 0..3, 0..32, 2..3]).squeeze_dim(3);
        let q: Tensor<4> = Tensor::stack(
            vec![
                mid.clone() - softplus(low),
                mid.clone(),
                mid + softplus(high),
            ],
            3,
        );
        let physical =
            q.clone() * scale.clone().reshape([b, 3, 1, 1]) + mu.clone().reshape([b, 3, 1, 1]);
        capture(trace, "normalized_quantiles", &q)?;
        capture(trace, "quantiles", &physical)?;
        Ok(ForwardTensors {
            normalized: q,
            physical,
            center: mu,
            scale,
        })
    }
    fn run(&self, input: &ForecastInput, traced: bool) -> Result<(Forecast, Vec<TraceTensor>)> {
        let b = input.batch();
        let mut trace = traced.then(Vec::new);
        let x = Tensor::<3>::from_data(
            TensorData::new(input.values().to_vec(), [b, 3, 128]),
            &self.device,
        );
        let ForwardTensors {
            physical,
            center: mu,
            scale,
            ..
        } = self.forward_inner(x, &mut trace)?;
        let quantiles = read(&physical)?;
        if quantiles.iter().any(|v| !v.is_finite())
            || quantiles
                .chunks_exact(3)
                .any(|q| q[0] > q[1] || q[1] > q[2])
        {
            return Err(Error::Backend("nonfinite/unordered output".into()));
        }
        Ok((
            Forecast {
                batch: b,
                quantile_levels: [0.1, 0.5, 0.9],
                quantiles,
                context_center: read(&mu)?,
                context_scale: read(&scale)?,
            },
            trace.unwrap_or_default(),
        ))
    }
}
