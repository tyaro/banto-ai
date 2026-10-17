//! R2P step 4: the full SmallForecaster on fixed artificial data, compared with
//! the committed Torch reference under the unchanged R0.1 tolerances. The
//! training forward is the inference `SmallForecaster::forward`, and its tensors
//! reach the loss without host readback. Conditions:
//! examples/configs/rust-r2p-full-model-fixtures-20261017.json.

use banto_ai::{
    checkpoint::expected_shapes,
    model::SmallForecaster,
    synthetic_checkpoint::sha256,
    training::{Parameter, clip_global_norm, loss_and_gradients, pinball_loss, read},
};
use burn::tensor::{Device, Tensor, TensorData};
use serde_json::Value;
use std::{
    cell::RefCell,
    collections::{BTreeMap, BTreeSet},
    fs,
    path::PathBuf,
};

const BUFFERS: [&str; 3] = ["scale_floor", "position", "time_mask"];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}
fn json(path: PathBuf) -> Value {
    serde_json::from_slice(&fs::read(path).unwrap()).unwrap()
}

/// Reference tensors by name, read from the float32 binary through the layout.
struct Reference {
    values: BTreeMap<String, Vec<f32>>,
    tolerance: Value,
    used: RefCell<BTreeSet<String>>,
}
impl Reference {
    fn load() -> Self {
        let dir = root().join("tests/fixtures/r2p-full");
        let raw = fs::read(dir.join("reference.f32")).unwrap();
        let values = json(dir.join("reference-layout.json"))
            .as_array()
            .unwrap()
            .iter()
            .map(|e| {
                let offset = e["offset"].as_u64().unwrap() as usize;
                let bytes = e["bytes"].as_u64().unwrap() as usize;
                let chunk = &raw[offset..offset + bytes];
                assert_eq!(sha256(chunk), e["sha256"].as_str().unwrap());
                let v = chunk
                    .chunks_exact(4)
                    .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
                    .collect();
                (e["name"].as_str().unwrap().to_string(), v)
            })
            .collect();
        let tolerance =
            json(root().join("../../examples/configs/rust-small-forecaster-r0-20261016-r0.1.json"))
                ["tolerance"]
                .clone();
        Self {
            values,
            tolerance,
            used: RefCell::new(BTreeSet::new()),
        }
    }
    fn get(&self, name: &str) -> &[f32] {
        self.used.borrow_mut().insert(name.to_string());
        self.values
            .get(name)
            .unwrap_or_else(|| panic!("no reference {name}"))
    }
    /// Every saved reference entry must have been compared or used as input.
    fn assert_all_used(&self) {
        let all: BTreeSet<String> = self.values.keys().cloned().collect();
        assert_eq!(*self.used.borrow(), all, "reference entries not compared");
    }
    /// Elementwise abs(rust-ref) <= atol + rtol*abs(ref).
    fn elementwise(&self, name: &str, rust: &[f32], kind: &str) {
        let reference = self.get(name);
        assert_eq!(rust.len(), reference.len(), "{name} length");
        assert!(rust.iter().all(|x| x.is_finite()), "{name} nonfinite");
        let tol = &self.tolerance[kind];
        let (atol, rtol) = (tol["atol"].as_f64().unwrap(), tol["rtol"].as_f64().unwrap());
        let failures: Vec<_> = rust
            .iter()
            .zip(reference)
            .enumerate()
            .filter(|(_, (a, b))| {
                (**a as f64 - **b as f64).abs() > atol + rtol * (**b as f64).abs()
            })
            .map(|(i, (a, b))| (i, *a, *b))
            .take(5)
            .collect();
        assert!(
            failures.is_empty(),
            "{name} ({kind}) element failures {failures:?}"
        );
    }
    /// R0.1's gradient L2 rule over all tensors together: relative L2 against a
    /// nonzero reference, otherwise the candidate's own L2 within atol.
    fn global_gradient_l2(&self, label: &str, names: &[String], prefix: &str, rust: &[Vec<f32>]) {
        let tol = &self.tolerance["gradient"];
        let (mut norm, mut delta, mut candidate) = (0f64, 0f64, 0f64);
        assert_eq!(names.len(), rust.len(), "{label} tensor count");
        for (name, values) in names.iter().zip(rust) {
            let reference = self.get(&format!("{prefix}{name}"));
            assert_eq!(values.len(), reference.len(), "{label} {name} length");
            for (&a, &b) in values.iter().zip(reference) {
                norm += (b as f64).powi(2);
                delta += (a as f64 - b as f64).powi(2);
                candidate += (a as f64).powi(2);
            }
        }
        if norm > 0.0 {
            let rel = delta.sqrt() / norm.sqrt();
            assert!(
                rel <= tol["relative_L2_max"].as_f64().unwrap(),
                "{label} global relative L2 {rel}"
            );
        } else {
            assert!(
                candidate.sqrt() <= tol["atol"].as_f64().unwrap(),
                "{label} zero-reference L2"
            );
        }
    }
}

/// Initial values from the fixture's rules: an integer divided by a power of
/// two, so the f64 arithmetic below is exact and the f32 cast loses nothing.
fn initial(name: &str, shape: &[usize]) -> Vec<f32> {
    let s = name.bytes().map(usize::from).sum::<usize>() % 257;
    let norm = name.contains(".norms.") || name.starts_with("final_norm.");
    let n: usize = shape.iter().product();
    let rule = |i: usize| -> f64 {
        if name == "horizon" {
            (((i * 29 + s) % 33) as f64 - 16.0) / 1024.0
        } else if norm && name.ends_with(".weight") {
            1.0 + (((i * 13 + s) % 9) as f64 - 4.0) / 64.0
        } else if norm && name.ends_with(".bias") {
            (((i * 11 + s) % 7) as f64 - 3.0) / 64.0
        } else if name.ends_with(".weight") {
            let a = if shape[1] <= 64 {
                1.0 / 8.0
            } else {
                1.0 / 16.0
            };
            (((i * 7919 + s) % 257) as f64 - 128.0) / 128.0 * a
        } else if name.ends_with(".bias") {
            (((i * 31 + s) % 17) as f64 - 8.0) / 256.0
        } else {
            panic!("no initialization rule for {name}")
        }
    };
    (0..n)
        .map(|i| {
            let v = rule(i);
            assert_eq!(v as f32 as f64, v, "{name}[{i}] not float32-exact");
            v as f32
        })
        .collect()
}

/// Batch k: context [2,3,128] and actual [2,3,32] from the fixture's formulas.
fn batch(k: usize) -> (Vec<f32>, Vec<f32>) {
    let mut context = Vec::new();
    for b in 0..2 {
        for c in 0..3 {
            for t in 0..128 {
                context.push(if c < 2 {
                    (((t * (c + 3) + 5 * b + k) % 16) as f32 - 8.0) / 4.0 + c as f32
                } else {
                    2.0 + ((t + b + k) % 2) as f32 / 16.0
                });
            }
        }
    }
    let mut actual = Vec::new();
    for b in 0..2 {
        for c in 0..3 {
            for h in 0..32 {
                actual.push((((h * 5 + 3 * c + b + k) % 11) as f32 - 5.0) / 2.0 + c as f32);
            }
        }
    }
    (context, actual)
}

struct Fixture {
    reference: Reference,
    parameters: Vec<Parameter>,
    buffers: BTreeMap<String, Tensor<1>>,
    device: Device,
}
impl Fixture {
    fn new() -> Self {
        let (reference, device) = (Reference::load(), Device::flex());
        let hashes = json(root().join("tests/fixtures/r2p-full/initial-parameters-sha256.json"));
        let mut parameters = Vec::new();
        for (name, shape) in expected_shapes() {
            if BUFFERS.contains(&name.as_str()) {
                continue;
            }
            let values = initial(&name, &shape);
            let bytes: Vec<u8> = values.iter().flat_map(|v| v.to_le_bytes()).collect();
            assert_eq!(sha256(&bytes), hashes[&name], "{name} initial values");
            parameters.push(Parameter::new(&name, shape, values, &device).unwrap());
        }
        assert_eq!(parameters.len(), 59);
        assert_eq!(
            parameters
                .iter()
                .map(|p| p.shape.iter().product::<usize>())
                .sum::<usize>(),
            109024
        );
        let flat = |v: Vec<f32>| {
            let n = v.len();
            Tensor::<1>::from_data(TensorData::new(v, [n]), &device)
        };
        let time_mask = (0..25)
            .map(|i| if i % 5 <= i / 5 { 1.0 } else { 0.0 })
            .collect();
        let buffers = BTreeMap::from([
            ("scale_floor".to_string(), flat(vec![0.5, 0.25, 0.125])),
            (
                "position".to_string(),
                flat(reference.get("buffer/position").to_vec()),
            ),
            ("time_mask".to_string(), flat(time_mask)),
        ]);
        Self {
            reference,
            parameters,
            buffers,
            device,
        }
    }
    /// The inference model with the given parameter tensors (leaves or plain).
    fn model(&self, tensors: &[Tensor<1>]) -> SmallForecaster {
        let mut state = self.buffers.clone();
        for (p, t) in self.parameters.iter().zip(tensors) {
            state.insert(p.name.clone(), t.clone());
        }
        SmallForecaster::from_named(state).unwrap()
    }
    fn tensors(&self, k: usize) -> (Tensor<3>, Tensor<3>) {
        let (context, actual) = batch(k);
        (
            Tensor::from_data(TensorData::new(context, [2, 3, 128]), &self.device),
            Tensor::from_data(TensorData::new(actual, [2, 3, 32]), &self.device),
        )
    }
    fn check_forward(&self, label: &str, model: &SmallForecaster, k: usize) -> Tensor<1> {
        let (context, actual) = self.tensors(k);
        let f = model.forward(context).unwrap();
        let r = &self.reference;
        r.elementwise(
            &format!("{label}/normalized-quantiles"),
            &read(&f.normalized).unwrap(),
            "normalized_activation",
        );
        r.elementwise(
            &format!("{label}/context-center"),
            &read(&f.center).unwrap(),
            "normalized_activation",
        );
        r.elementwise(
            &format!("{label}/context-scale"),
            &read(&f.scale).unwrap(),
            "normalized_activation",
        );
        let loss = pinball_loss(f.normalized, actual, f.center, f.scale);
        r.elementwise(
            &format!("{label}/loss"),
            &read(&loss).unwrap(),
            "normalized_loss",
        );
        loss
    }
}

#[test]
fn full_model_loss_and_all_gradients_match_reference() {
    let fx = Fixture::new();
    let fixture =
        json(root().join("../../examples/configs/rust-r2p-full-model-fixtures-20261017.json"));
    let k = |id: &str| fixture["batches"]["k"][id].as_u64().unwrap() as usize;

    // Batch A through the shared forward on fresh autodiff leaves.
    let (_, gradients) = loss_and_gradients(&fx.parameters, |leaves| {
        Ok(fx.check_forward("batchA", &fx.model(leaves), k("A")))
    })
    .unwrap();
    let names: Vec<String> = fx.parameters.iter().map(|p| p.name.clone()).collect();
    let raw: Vec<Vec<f32>> = gradients.iter().map(|g| read(g).unwrap()).collect();
    for (name, g) in names.iter().zip(&raw) {
        fx.reference
            .elementwise(&format!("gradient/{name}"), g, "gradient");
    }
    fx.reference
        .global_gradient_l2("raw gradients", &names, "gradient/", &raw);

    let clipped = clip_global_norm(gradients, 1.0).unwrap();
    fx.reference.elementwise(
        "clip/global-norm",
        &read(&clipped.norm).unwrap(),
        "gradient",
    );
    fx.reference.elementwise(
        "clip/coefficient",
        &read(&clipped.coefficient).unwrap(),
        "gradient",
    );
    let clipped: Vec<Vec<f32>> = clipped.gradients.iter().map(|g| read(g).unwrap()).collect();
    for (name, g) in names.iter().zip(&clipped) {
        fx.reference
            .elementwise(&format!("clipped-gradient/{name}"), g, "gradient");
    }
    fx.reference
        .global_gradient_l2("clipped gradients", &names, "clipped-gradient/", &clipped);

    // Batch B with the initial (plain) parameters: no optimizer update in step 4.
    let plain: Vec<Tensor<1>> = fx.parameters.iter().map(|p| p.value.clone()).collect();
    fx.check_forward("batchB", &fx.model(&plain), k("B"));
    fx.reference.assert_all_used();
}

#[test]
fn model_rejects_an_incomplete_tensor_set() {
    let fx = Fixture::new();
    let mut state = fx.buffers.clone();
    for p in &fx.parameters[1..] {
        state.insert(p.name.clone(), p.value.clone());
    }
    assert!(SmallForecaster::from_named(state).is_err());
}
