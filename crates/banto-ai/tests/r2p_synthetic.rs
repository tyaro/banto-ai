//! R2P step 2: Rust loss/gradient, global clip and AdamW against the committed
//! artificial Torch reference under the unchanged R0.1 tolerances, plus the six
//! fixed invalid-component rejections. Toy training and resume are step 3.

use banto_ai::training::{
    AdamW, AdamWState, LossInput, Parameter, clip_global_norm, ordered_gradients, read,
};
use burn::tensor::{Device, Tensor, TensorData};
use serde_json::Value;
use std::{collections::BTreeMap, fs, path::PathBuf};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}
fn json(path: PathBuf) -> Value {
    serde_json::from_slice(&fs::read(&path).unwrap()).unwrap()
}
fn fixtures() -> Value {
    json(root().join("../../examples/configs/rust-r2p-synthetic-fixtures-20261016.json"))
}
fn floats(v: &Value) -> Vec<f32> {
    v.as_array()
        .unwrap()
        .iter()
        .map(|x| x.as_f64().unwrap() as f32)
        .collect()
}
fn dims<const N: usize>(v: &Value) -> [usize; N] {
    let d: Vec<usize> = v
        .as_array()
        .unwrap()
        .iter()
        .map(|x| x.as_u64().unwrap() as usize)
        .collect();
    d.try_into().unwrap()
}

struct Reference {
    values: BTreeMap<String, Vec<f32>>,
    tolerance: Value,
}
impl Reference {
    fn load() -> Self {
        let layout = json(root().join("tests/fixtures/r2p/reference-layout.json"));
        let values = layout
            .as_array()
            .unwrap()
            .iter()
            .map(|t| {
                (
                    t["name"].as_str().unwrap().to_string(),
                    floats(&t["values"]),
                )
            })
            .collect();
        let tolerance =
            json(root().join("../../examples/configs/rust-small-forecaster-r0-20261016-r0.1.json"))
                ["tolerance"]
                .clone();
        Self { values, tolerance }
    }
    /// Elementwise abs(rust-ref)<=atol+rtol*abs(ref); gradients also need the
    /// global relative L2 bound, or candidate L2<=atol when the reference is zero.
    fn gate(&self, name: &str, rust: &[f32], kind: &str) {
        let reference = self
            .values
            .get(name)
            .unwrap_or_else(|| panic!("no reference {name}"));
        assert_eq!(rust.len(), reference.len(), "{name} length");
        assert!(rust.iter().all(|x| x.is_finite()), "{name} nonfinite");
        let tol = &self.tolerance[kind];
        let (atol, rtol) = (tol["atol"].as_f64().unwrap(), tol["rtol"].as_f64().unwrap());
        let mut failures = Vec::new();
        for (i, (&a, &b)) in rust.iter().zip(reference).enumerate() {
            let (a, b) = (a as f64, b as f64);
            if (a - b).abs() > atol + rtol * b.abs() {
                failures.push((i, a, b));
            }
        }
        assert!(
            failures.is_empty(),
            "{name} ({kind}) element failures {failures:?}"
        );
        if kind == "gradient" {
            let norm = reference
                .iter()
                .map(|&b| (b as f64).powi(2))
                .sum::<f64>()
                .sqrt();
            let delta = rust
                .iter()
                .zip(reference)
                .map(|(&a, &b)| (a as f64 - b as f64).powi(2))
                .sum::<f64>()
                .sqrt();
            if norm > 0.0 {
                let bound = tol["relative_L2_max"].as_f64().unwrap();
                assert!(delta / norm <= bound, "{name} relative L2 {}", delta / norm);
            } else {
                let candidate = rust.iter().map(|&a| (a as f64).powi(2)).sum::<f64>().sqrt();
                assert!(candidate <= atol, "{name} zero-reference L2 {candidate}");
            }
        }
    }
}

fn device() -> Device {
    Device::flex()
}
fn flat(device: &Device, values: Vec<f32>) -> Tensor<1> {
    let n = values.len();
    Tensor::from_data(TensorData::new(values, [n]), device)
}
fn loss_input(case: &Value) -> LossInput {
    let shape: [usize; 4] = dims(&case["shape"]);
    let [b, c, h, _] = shape;
    LossInput::new(
        shape,
        floats(&case["prediction"]),
        [b, c, h],
        floats(&case["actual"]),
        floats(&case["center"]),
        floats(&case["scale"]),
    )
    .unwrap()
}
fn recipe(fx: &Value) -> AdamW {
    let r = &fx["optimizer_recipe"];
    assert_eq!(r["weight_decay"].as_f64().unwrap(), 0.01);
    assert!(r["all_parameters_decay"].as_bool().unwrap());
    AdamW {
        lr: r["lr"].as_f64().unwrap(),
        betas: (
            r["betas"][0].as_f64().unwrap(),
            r["betas"][1].as_f64().unwrap(),
        ),
        eps: r["eps"].as_f64().unwrap(),
        weight_decay: r["weight_decay"].as_f64().unwrap(),
    }
}
fn optimizer_parameters(fx: &Value, device: &Device) -> Vec<Parameter> {
    fx["optimizer_parameter_order"]
        .as_array()
        .unwrap()
        .iter()
        .map(|n| {
            let n = n.as_str().unwrap();
            let p = &fx["optimizer_initial_parameters"][n];
            Parameter::new(
                n,
                dims::<1>(&p["shape"]).to_vec(),
                floats(&p["values"]),
                device,
            )
            .unwrap()
        })
        .collect()
}
fn named(parameters: &[Parameter], device: &Device, groups: &Value) -> Vec<(String, Tensor<1>)> {
    parameters
        .iter()
        .zip(groups.as_array().unwrap())
        .map(|(p, g)| (p.name.clone(), flat(device, floats(g))))
        .collect()
}

#[test]
fn loss_and_prediction_gradient_match_reference() {
    let (fx, reference, device) = (fixtures(), Reference::load(), device().autodiff());
    let cases = fx["loss_cases"].as_array().unwrap();
    assert_eq!(cases.len(), 7);
    for case in cases {
        let id = case["id"].as_str().unwrap();
        let input = loss_input(case);
        let prediction = input.prediction(&device).require_grad();
        let loss = input.loss(prediction.clone());
        let grads = loss.backward();
        let gradient = prediction.grad(&grads).expect("prediction gradient");
        reference.gate(
            &format!("{id}/loss"),
            &read(&loss).unwrap(),
            "normalized_loss",
        );
        reference.gate(
            &format!("{id}/gradient"),
            &read(&gradient).unwrap(),
            "gradient",
        );
    }
}

#[test]
fn global_clip_matches_reference() {
    let (fx, reference, device) = (fixtures(), Reference::load(), device());
    let cases = fx["clip_cases"].as_array().unwrap();
    assert_eq!(cases.len(), 4);
    for case in cases {
        let id = case["id"].as_str().unwrap();
        let gradients = case["gradients"]
            .as_array()
            .unwrap()
            .iter()
            .map(|g| flat(&device, floats(g)))
            .collect();
        let clipped = clip_global_norm(gradients, 1.0).unwrap();
        reference.gate(
            &format!("{id}/global-norm"),
            &read(&clipped.norm).unwrap(),
            "gradient",
        );
        reference.gate(
            &format!("{id}/clip-coefficient"),
            &read(&clipped.coefficient).unwrap(),
            "gradient",
        );
        for (i, g) in clipped.gradients.iter().enumerate() {
            reference.gate(
                &format!("{id}/clipped-gradient/{i}"),
                &read(g).unwrap(),
                "gradient",
            );
        }
    }
}

#[test]
fn adamw_single_updates_match_reference() {
    let (fx, reference, device) = (fixtures(), Reference::load(), device());
    let optimizer = recipe(&fx);
    let cases = fx["optimizer_cases"].as_array().unwrap();
    assert_eq!(cases.len(), 6);
    for case in cases {
        let id = case["id"].as_str().unwrap();
        let mut parameters = optimizer_parameters(&fx, &device);
        let step = case["step_before"].as_u64().unwrap();
        let mut state = AdamWState {
            step,
            m: case["m_before"]
                .as_array()
                .unwrap()
                .iter()
                .map(|x| flat(&device, floats(x)))
                .collect(),
            v: case["v_before"]
                .as_array()
                .unwrap()
                .iter()
                .map(|x| flat(&device, floats(x)))
                .collect(),
        };
        let gradients =
            ordered_gradients(&parameters, named(&parameters, &device, &case["gradients"]))
                .unwrap();
        let clipped = clip_global_norm(gradients, 1.0).unwrap();
        for (i, g) in clipped.gradients.iter().enumerate() {
            reference.gate(
                &format!("{id}/clipped-gradient/{i}"),
                &read(g).unwrap(),
                "gradient",
            );
        }
        optimizer
            .step(&mut parameters, &clipped.gradients, &mut state)
            .unwrap();
        assert_eq!(state.step, step + 1, "{id} step");
        if id == "O0_zero_fresh_decay" {
            // Zero gradient and moments: the update is exactly the decoupled decay,
            // which is below the one-step tolerance, so check it bit for bit.
            let decay = (1.0 - optimizer.lr * optimizer.weight_decay) as f32;
            for (p, initial) in parameters.iter().zip(optimizer_parameters(&fx, &device)) {
                let expected: Vec<f32> = read(&initial.value)
                    .unwrap()
                    .iter()
                    .map(|x| x * decay)
                    .collect();
                assert_eq!(read(&p.value).unwrap(), expected, "{id} decay");
                assert_ne!(
                    read(&p.value).unwrap(),
                    read(&initial.value).unwrap(),
                    "{id} decay applied"
                );
            }
        }
        for (i, p) in parameters.iter().enumerate() {
            let after = format!("{id}/after");
            reference.gate(
                &format!("{after}/parameter/{i}"),
                &read(&p.value).unwrap(),
                "one_step_parameter",
            );
            reference.gate(
                &format!("{after}/moment1/{i}"),
                &read(&state.m[i]).unwrap(),
                "first_moment",
            );
            reference.gate(
                &format!("{after}/moment2/{i}"),
                &read(&state.v[i]).unwrap(),
                "second_moment",
            );
            let torch_step = &reference.values[&format!("{after}/step-tensor/{i}")];
            assert_eq!(torch_step, &vec![state.step as f32], "{id} step tensor");
        }
    }
}

#[test]
fn invalid_components_are_rejected() {
    let (fx, device) = (fixtures(), device());
    let ids: Vec<&str> = fx["invalid_component_cases"]
        .as_array()
        .unwrap()
        .iter()
        .map(|x| x.as_str().unwrap())
        .collect();
    assert_eq!(ids.len(), 6);
    let l0 = &fx["loss_cases"][0];
    let build = |mutate: &dyn Fn(&mut [Vec<f32>; 4]), actual_shape: [usize; 3]| {
        let mut v = ["prediction", "actual", "center", "scale"].map(|k| floats(&l0[k]));
        mutate(&mut v);
        let [p, a, c, s] = v;
        LossInput::new([1, 1, 1, 3], p, actual_shape, a, c, s)
    };
    assert!(build(&|_| {}, [1, 1, 1]).is_ok());
    assert!(build(&|v| v[1] = vec![0.0, 0.0], [1, 1, 2]).is_err(), "I0");
    assert!(build(&|v| v[0][0] = f32::NAN, [1, 1, 1]).is_err(), "I1");
    assert!(
        build(&|v| v[1][0] = f32::INFINITY, [1, 1, 1]).is_err(),
        "I2"
    );
    assert!(build(&|v| v[3][0] = 0.0, [1, 1, 1]).is_err(), "I3");

    let parameters = optimizer_parameters(&fx, &device);
    let o1 = &fx["optimizer_cases"][1];
    assert_eq!(o1["id"], "O1_signed_fresh");
    let mut missing = named(&parameters, &device, &o1["gradients"]);
    missing.retain(|(n, _)| n != "p.bias");
    assert!(ordered_gradients(&parameters, missing).is_err(), "I4");
    let mut duplicate = named(&parameters, &device, &o1["gradients"]);
    duplicate.insert(1, ("p.weight".into(), flat(&device, vec![0.0, 0.0])));
    assert!(
        ordered_gradients(&parameters, duplicate).is_err(),
        "I5 duplicate"
    );
    let mut unknown = named(&parameters, &device, &o1["gradients"]);
    unknown.push(("p.other".into(), flat(&device, vec![0.0])));
    assert!(
        ordered_gradients(&parameters, unknown).is_err(),
        "I5 unknown"
    );
}
