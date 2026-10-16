//! Pinned CARE neutral reference reader. Expected hashes come from a trusted manifest.
use crate::{Error, Result};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
#[derive(Deserialize)]
struct Layout {
    schema: String,
    tensors: Vec<Entry>,
}
#[derive(Deserialize)]
struct Entry {
    name: String,
    shape: Vec<usize>,
    dtype: String,
    offset_bytes: usize,
    length_bytes: usize,
}
#[derive(Clone, Debug)]
pub struct NeutralModel {
    pub(crate) tensors: BTreeMap<String, Vec<f32>>,
}
pub fn expected_shapes() -> BTreeMap<String, Vec<usize>> {
    let mut s = BTreeMap::new();
    for (n, d) in [
        ("horizon", vec![64]),
        ("scale_floor", vec![3]),
        ("position", vec![5, 64]),
        ("time_mask", vec![5, 5]),
        ("patch.weight", vec![64, 32]),
        ("patch.bias", vec![64]),
        ("final_norm.weight", vec![64]),
        ("final_norm.bias", vec![64]),
        ("head.weight", vec![96, 64]),
        ("head.bias", vec![96]),
    ] {
        s.insert(n.into(), d);
    }
    for i in 0..2 {
        for a in ["temporal", "variate"] {
            for n in ["q", "k", "v", "out"] {
                s.insert(format!("blocks.{i}.{a}.{n}.weight"), vec![64, 64]);
                s.insert(format!("blocks.{i}.{a}.{n}.bias"), vec![64]);
            }
        }
        for j in 0..3 {
            for f in ["weight", "bias"] {
                s.insert(format!("blocks.{i}.norms.{j}.{f}"), vec![64]);
            }
        }
        for (j, o, k) in [(0, 128, 64), (2, 64, 128)] {
            s.insert(format!("blocks.{i}.ff.{j}.weight"), vec![o, k]);
            s.insert(format!("blocks.{i}.ff.{j}.bias"), vec![o]);
        }
    }
    s
}
pub fn sha256(b: &[u8]) -> String {
    format!("{:x}", Sha256::digest(b))
}
impl NeutralModel {
    /// Inference import only; optimizer/RNG bytes are validated but not used.
    pub fn from_reference(
        layout: &[u8],
        payload: &[u8],
        layout_sha: &str,
        payload_sha: &str,
    ) -> Result<Self> {
        if layout.len() > 256 * 1024 || payload.len() > 32 * 1024 * 1024 {
            return Err(Error::Model("file size cap".into()));
        }
        if sha256(layout) != layout_sha || sha256(payload) != payload_sha {
            return Err(Error::Integrity("reference digest mismatch".into()));
        }
        let l: Layout = serde_json::from_slice(layout)?;
        if l.schema != "banto.care-learning-reference.v1" || l.tensors.len() > 256 {
            return Err(Error::Model("schema/count".into()));
        }
        let shapes = expected_shapes();
        let mut names = BTreeSet::new();
        let mut model = BTreeMap::new();
        let mut previous_end = 0;
        for e in &l.tensors {
            if !names.insert(&e.name) {
                return Err(Error::Model("duplicate tensor".into()));
            }
            let width = match e.dtype.as_str() {
                "float32-le" => 4,
                "bool-u8" | "uint8" => 1,
                _ => return Err(Error::Model("dtype".into())),
            };
            let n = e
                .shape
                .iter()
                .try_fold(1usize, |n, &d| n.checked_mul(d))
                .ok_or_else(|| Error::Model("shape overflow".into()))?;
            let len = n
                .checked_mul(width)
                .ok_or_else(|| Error::Model("length overflow".into()))?;
            let end = e
                .offset_bytes
                .checked_add(len)
                .ok_or_else(|| Error::Model("offset overflow".into()))?;
            if len != e.length_bytes
                || e.offset_bytes < previous_end
                || end > payload.len()
                || e.offset_bytes - previous_end > 3
                || payload[previous_end..e.offset_bytes]
                    .iter()
                    .any(|x| *x != 0)
            {
                return Err(Error::Model("bounds/overlap/padding".into()));
            }
            let b = &payload[e.offset_bytes..end];
            previous_end = end;
            let values: Vec<f32> = if width == 4 {
                b.chunks_exact(4)
                    .map(|v| f32::from_le_bytes(v.try_into().unwrap()))
                    .collect()
            } else {
                if e.dtype == "bool-u8" && b.iter().any(|v| *v > 1) {
                    return Err(Error::Model("bool byte".into()));
                }
                b.iter().map(|v| *v as f32).collect()
            };
            if values.iter().any(|v| !v.is_finite()) {
                return Err(Error::Model("nonfinite state".into()));
            }
            if let Some(n) = e.name.strip_prefix("model::") {
                let dtype = if n == "time_mask" {
                    "bool-u8"
                } else {
                    "float32-le"
                };
                if shapes.get(n) != Some(&e.shape) || e.dtype != dtype {
                    return Err(Error::Model(format!("shape/dtype {n}")));
                }
                model.insert(n.into(), values);
            } else if let Some(rest) = e.name.strip_prefix("adamw::") {
                let (n, f) = rest
                    .rsplit_once("::")
                    .ok_or_else(|| Error::Model("optimizer name".into()))?;
                let shape = shapes
                    .get(n)
                    .filter(|_| !["scale_floor", "position", "time_mask"].contains(&n))
                    .ok_or_else(|| Error::Model("optimizer identity".into()))?;
                if e.dtype != "float32-le"
                    || match f {
                        "step" => {
                            !e.shape.is_empty() || values[0] < 0.0 || values[0].fract() != 0.0
                        }
                        "exp_avg" => &e.shape != shape,
                        "exp_avg_sq" => &e.shape != shape || values.iter().any(|v| *v < 0.0),
                        _ => true,
                    }
                {
                    return Err(Error::Model("optimizer field".into()));
                }
            } else if e.name != "torch_rng_backend_specific" || e.dtype != "uint8" {
                return Err(Error::Model("unexpected state".into()));
            }
        }
        if previous_end != payload.len() || model.len() != shapes.len() {
            return Err(Error::Model("incomplete/unlisted state".into()));
        }
        if model["scale_floor"].iter().any(|v| *v <= 0.0) {
            return Err(Error::Model("scale floor".into()));
        }
        let causal: Vec<f32> = (0..25)
            .map(|i| if i % 5 <= i / 5 { 1.0 } else { 0.0 })
            .collect();
        if model["time_mask"] != causal {
            return Err(Error::Model("noncausal mask".into()));
        }
        Ok(Self { tensors: model })
    }
    pub fn parameter_count(&self) -> usize {
        109024
    }
    pub fn scale_floor(&self) -> [f32; 3] {
        self.tensors["scale_floor"].as_slice().try_into().unwrap()
    }
}
