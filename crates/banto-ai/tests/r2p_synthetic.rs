//! R2P against the committed artificial Torch reference under the unchanged
//! R0.1 tolerances. Step 2: loss/gradient, global clip, AdamW and the six
//! invalid-component rejections. Step 3: the toy affine model's continuous
//! eight updates, and a checkpoint resumed in separate processes.

use banto_ai::{
    synthetic_checkpoint::{
        Binding, COMMIT, MANIFEST, PAYLOAD, TrainingState, WriterStop, commit, encode,
        read_checkpoint, sha256, write,
    },
    training::{
        AdamW, AdamWState, LossInput, Parameter, clip_global_norm, ordered_gradients, pinball_loss,
        read, train_step,
    },
};
use burn::tensor::{Device, Tensor, TensorData};
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    env, fs,
    path::{Path, PathBuf},
    process::Command,
    time::{SystemTime, UNIX_EPOCH},
};

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
fn shape(v: &Value) -> Vec<usize> {
    v.as_array()
        .unwrap()
        .iter()
        .map(|x| x.as_u64().unwrap() as usize)
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
        let loss = input.loss(prediction.clone()).unwrap();
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

// ---- Step 3: toy training, checkpoint and resume ----

const FIXTURES: &str = "../../examples/configs/rust-r2p-synthetic-fixtures-20261016.json";
const CHILD_DIR: &str = "BANTO_R2P_CHILD_DIR";

struct Toy {
    fx: Value,
    optimizer: AdamW,
    binding: Binding,
}
impl Toy {
    fn new() -> Self {
        let fx = fixtures();
        let toy = &fx["toy_training"];
        let parameter_order = toy["parameter_order"]
            .as_array()
            .unwrap()
            .iter()
            .map(|n| {
                let n = n.as_str().unwrap();
                (n.to_string(), shape(&toy["parameters"][n]["shape"]))
            })
            .collect();
        let buffers = ["center", "scale"]
            .map(|b| {
                let t = &toy["buffers"][b];
                (
                    b.to_string(),
                    dims::<3>(&t["shape"]).to_vec(),
                    floats(&t["values"]),
                )
            })
            .to_vec();
        let schedule = toy["schedule"]
            .as_array()
            .unwrap()
            .iter()
            .map(|x| x.as_str().unwrap().to_string())
            .collect();
        let binding = Binding {
            parameter_order,
            buffers,
            schedule,
            fixture_sha256: sha256(&fs::read(root().join(FIXTURES)).unwrap()),
            recipe: fx["optimizer_recipe"].clone(),
        };
        Self {
            optimizer: recipe(&fx),
            fx,
            binding,
        }
    }
    fn initial(&self, device: &Device) -> TrainingState {
        let toy = &self.fx["toy_training"];
        let parameters: Vec<Parameter> = self
            .binding
            .parameter_order
            .iter()
            .map(|(n, shape)| {
                Parameter::new(
                    n,
                    shape.clone(),
                    floats(&toy["parameters"][n]["values"]),
                    device,
                )
                .unwrap()
            })
            .collect();
        let optimizer = AdamWState::zeros(&parameters);
        TrainingState {
            parameters,
            optimizer,
            next_position: 0,
        }
    }
    /// q = x @ weight.T + bias for x [1,1,2,2], giving q [1,1,2,3].
    fn forward(weight: Tensor<1>, bias: Tensor<1>, x: &[f32]) -> Tensor<4> {
        let device = weight.device();
        let x = Tensor::<4>::from_data(TensorData::new(x.to_vec(), [1, 1, 2, 2]), &device);
        let w = weight.reshape([3, 2]).transpose().reshape([1, 1, 2, 3]);
        x.matmul(w) + bias.reshape([1, 1, 1, 3])
    }
    fn probe(&self, state: &TrainingState) -> Vec<f32> {
        let p = &state.parameters;
        let x = floats(&self.fx["toy_training"]["probe_x"]);
        read(&Self::forward(p[0].value.clone(), p[1].value.clone(), &x)).unwrap()
    }
    fn batch(&self, position: usize) -> (Vec<f32>, Vec<f32>) {
        let id = &self.binding.schedule[position];
        let b = self.fx["toy_training"]["batch_table"]
            .as_array()
            .unwrap()
            .iter()
            .find(|b| b["id"] == *id.as_str())
            .unwrap();
        (floats(&b["x"]), floats(&b["target"]))
    }
    /// One scheduled update; returns the pre-update prediction and the record.
    fn update(&self, state: &mut TrainingState) -> (Vec<f32>, banto_ai::training::StepRecord) {
        let (x, target) = self.batch(state.next_position);
        let p = &state.parameters;
        let prediction = read(&Self::forward(p[0].value.clone(), p[1].value.clone(), &x)).unwrap();
        let buffer = |i: usize| self.binding.buffers[i].2.clone();
        let record = train_step(
            &mut state.parameters,
            &mut state.optimizer,
            &self.optimizer,
            1.0,
            |leaves| {
                let device = leaves[0].device();
                let q = Self::forward(leaves[0].clone(), leaves[1].clone(), &x);
                let t = |v: Vec<f32>, d: [usize; 3]| {
                    Tensor::<3>::from_data(TensorData::new(v, d), &device)
                };
                pinball_loss(
                    q,
                    t(target, [1, 1, 2]),
                    t(buffer(0), [1, 1, 1]),
                    t(buffer(1), [1, 1, 1]),
                )
            },
        )
        .unwrap();
        state.next_position += 1;
        assert_eq!(state.optimizer.step as usize, state.next_position);
        (prediction, record)
    }
    fn payload(&self, state: &TrainingState) -> Vec<u8> {
        encode(state, &self.binding).unwrap().0
    }
}

fn fresh_dir(label: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let dir = env::temp_dir().join(format!("banto-r2p-{label}-{}-{nanos}", std::process::id()));
    fs::create_dir(&dir).unwrap();
    dir
}
fn floats_bytes(values: &[f32]) -> Vec<u8> {
    values.iter().flat_map(|v| v.to_le_bytes()).collect()
}
fn run_child(test: &str, dir: &Path) {
    let output = Command::new(env::current_exe().unwrap())
        .args([
            "--ignored",
            "--exact",
            test,
            "--nocapture",
            "--test-threads=1",
        ])
        .env(CHILD_DIR, dir)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{test} failed:\n{}\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.contains("test result: ok. 1 passed"),
        "{test} did not run:\n{stdout}"
    );
}
fn dir_hashes(dir: &Path) -> BTreeMap<String, String> {
    fs::read_dir(dir)
        .unwrap()
        .map(|e| e.unwrap().path())
        .map(|p| {
            (
                p.file_name().unwrap().to_string_lossy().into(),
                sha256(&fs::read(&p).unwrap()),
            )
        })
        .collect()
}

/// Trajectory B in its own process (launched by the resume test): four updates,
/// commit step 4, then observe the cancellation at the next update boundary
/// without starting update 5. Saves the state bytes after every update.
#[test]
#[ignore = "child process of toy_training_resumes_exactly_and_matches_reference"]
fn child_b_cancel_after_four() {
    let Some(dir) = env::var_os(CHILD_DIR) else {
        return;
    };
    let (toy, device) = (Toy::new(), device());
    let mut state = toy.initial(&device);
    let mut cancelled = false;
    while state.next_position < toy.binding.schedule.len() {
        if cancelled {
            break;
        }
        toy.update(&mut state);
        let k = state.next_position;
        fs::write(
            Path::new(&dir).join(format!("b-payload-{k}.f32")),
            toy.payload(&state),
        )
        .unwrap();
        if k == 4 {
            write(&Path::new(&dir).join("b-step4"), &state, &toy.binding, None).unwrap();
            cancelled = true;
        }
    }
    assert_eq!((state.optimizer.step, state.next_position), (4, 4));
}

/// Trajectory C in its own process (launched by the resume test): restore B's
/// checkpoint, record the probe before update 5, finish the schedule and commit
/// step 8. Saves the state bytes at the restore and after every update.
#[test]
#[ignore = "child process of toy_training_resumes_exactly_and_matches_reference"]
fn child_c_restore_and_finish() {
    let Some(dir) = env::var_os(CHILD_DIR) else {
        return;
    };
    let (toy, device, dir) = (Toy::new(), device(), PathBuf::from(dir));
    let mut state = read_checkpoint(&dir.join("b-step4"), &toy.binding, &device).unwrap();
    assert_eq!((state.optimizer.step, state.next_position), (4, 4));
    let mut probes = toy.probe(&state);
    let save = |state: &TrainingState| {
        let k = state.next_position;
        fs::write(dir.join(format!("c-payload-{k}.f32")), toy.payload(state)).unwrap();
    };
    save(&state);
    while state.next_position < toy.binding.schedule.len() {
        toy.update(&mut state);
        probes.extend(toy.probe(&state));
        save(&state);
    }
    fs::write(dir.join("c-probes.f32"), floats_bytes(&probes)).unwrap();
    write(&dir.join("c-step8"), &state, &toy.binding, None).unwrap();
}

#[test]
fn toy_training_resumes_exactly_and_matches_reference() {
    let (toy, reference, device) = (Toy::new(), Reference::load(), device());
    // A: the continuous eight updates, each compared with the Torch reference.
    let mut a = toy.initial(&device);
    let mut probes = vec![toy.probe(&a)];
    reference.gate("toy/probe/0", &probes[0], "normalized_activation");
    let mut payloads = vec![toy.payload(&a)];
    while a.next_position < toy.binding.schedule.len() {
        let (prediction, record) = toy.update(&mut a);
        let k = a.next_position;
        let label = format!("toy/update{k}");
        let (loss_kind, parameter_kind) = match k {
            1 => ("normalized_loss", "one_step_parameter"),
            _ => ("eight_step_loss", "eight_step_parameter"),
        };
        reference.gate(
            &format!("{label}/prediction"),
            &prediction,
            "normalized_activation",
        );
        reference.gate(
            &format!("{label}/loss"),
            &read(&record.loss).unwrap(),
            loss_kind,
        );
        for i in 0..a.parameters.len() {
            let raw = read(&record.raw_gradients[i]).unwrap();
            let clipped = read(&record.clipped.gradients[i]).unwrap();
            reference.gate(&format!("{label}/raw-gradient/{i}"), &raw, "gradient");
            reference.gate(
                &format!("{label}/clipped-gradient/{i}"),
                &clipped,
                "gradient",
            );
            let after = format!("{label}/after");
            let value = read(&a.parameters[i].value).unwrap();
            reference.gate(&format!("{after}/parameter/{i}"), &value, parameter_kind);
            reference.gate(
                &format!("{after}/moment1/{i}"),
                &read(&a.optimizer.m[i]).unwrap(),
                "first_moment",
            );
            reference.gate(
                &format!("{after}/moment2/{i}"),
                &read(&a.optimizer.v[i]).unwrap(),
                "second_moment",
            );
            assert_eq!(
                reference.values[&format!("{after}/step-tensor/{i}")],
                vec![k as f32]
            );
        }
        probes.push(toy.probe(&a));
        reference.gate(
            &format!("toy/probe/{k}"),
            &probes[k],
            "normalized_activation",
        );
        payloads.push(toy.payload(&a));
    }

    // B and C in fresh processes; same-backend state must match A byte for byte.
    let dir = fresh_dir("resume");
    run_child("child_b_cancel_after_four", &dir);
    let b = dir.join("b-step4");
    assert_eq!(
        fs::read(b.join(PAYLOAD)).unwrap(),
        payloads[4],
        "B step 4 state"
    );
    for k in 1..=4 {
        let saved = fs::read(dir.join(format!("b-payload-{k}.f32"))).unwrap();
        assert_eq!(saved, payloads[k], "B state after update {k}");
    }
    assert!(!dir.join("b-payload-5.f32").exists(), "B started update 5");
    let manifest: Value = serde_json::from_slice(&fs::read(b.join(MANIFEST)).unwrap()).unwrap();
    assert_eq!(
        (
            manifest["global_step"].as_u64(),
            manifest["next_position"].as_u64()
        ),
        (Some(4), Some(4))
    );
    let committed = dir_hashes(&b);
    run_child("child_c_restore_and_finish", &dir);
    assert_eq!(
        fs::read(dir.join("c-step8").join(PAYLOAD)).unwrap(),
        toy.payload(&a),
        "C step 8 state"
    );
    for k in 4..=8 {
        let saved = fs::read(dir.join(format!("c-payload-{k}.f32"))).unwrap();
        assert_eq!(saved, payloads[k], "C state at step {k}");
    }
    let a_probes: Vec<f32> = probes[4..].concat();
    assert_eq!(
        fs::read(dir.join("c-probes.f32")).unwrap(),
        floats_bytes(&a_probes),
        "probes 4..8"
    );

    // Eight invalid checkpoints, each a fresh copy of B; none may load.
    let copy = |name: &str| {
        let target = dir.join(name);
        fs::create_dir(&target).unwrap();
        for f in [PAYLOAD, MANIFEST, COMMIT] {
            fs::copy(b.join(f), target.join(f)).unwrap();
        }
        target
    };
    let remanifest = |dir: &Path, edit: &dyn Fn(&mut Value, &mut Vec<u8>)| {
        let mut manifest: Value =
            serde_json::from_slice(&fs::read(dir.join(MANIFEST)).unwrap()).unwrap();
        let mut payload = fs::read(dir.join(PAYLOAD)).unwrap();
        edit(&mut manifest, &mut payload);
        manifest["payload_sha256"] = sha256(&payload).into();
        fs::write(dir.join(PAYLOAD), &payload).unwrap();
        let bytes = serde_json::to_vec_pretty(&manifest).unwrap();
        fs::write(dir.join(MANIFEST), &bytes).unwrap();
        fs::remove_file(dir.join(COMMIT)).unwrap();
        commit(dir, &bytes).unwrap();
    };
    let entry = |m: &Value, role: &str, name: &str| {
        m["entries"]
            .as_array()
            .unwrap()
            .iter()
            .position(|e| e["role"] == role && e["name"] == name)
            .unwrap()
    };
    let mut rejected = Vec::new();
    let k0 = copy("k0");
    let mut payload = fs::read(k0.join(PAYLOAD)).unwrap();
    payload.pop();
    fs::write(k0.join(PAYLOAD), payload).unwrap();
    rejected.push(k0);
    let k1 = copy("k1");
    let mut payload = fs::read(k1.join(PAYLOAD)).unwrap();
    payload[0] ^= 1;
    fs::write(k1.join(PAYLOAD), payload).unwrap();
    rejected.push(k1);
    let k2 = copy("k2");
    remanifest(&k2, &|m, _| {
        let i = entry(m, "moment1", "toy.bias");
        m["entries"].as_array_mut().unwrap().remove(i);
    });
    rejected.push(k2);
    let k3 = copy("k3");
    remanifest(&k3, &|m, _| {
        let i = entry(m, "parameter", "toy.weight");
        let duplicate = m["entries"][i].clone();
        m["entries"]
            .as_array_mut()
            .unwrap()
            .insert(i + 1, duplicate);
    });
    rejected.push(k3);
    let k4 = copy("k4");
    remanifest(&k4, &|m, payload| {
        let i = entry(m, "moment2", "toy.weight");
        let offset = m["entries"][i]["offset"].as_u64().unwrap() as usize;
        payload[offset..offset + 4].copy_from_slice(&(-1.0f32).to_le_bytes());
        let bytes = m["entries"][i]["bytes"].as_u64().unwrap() as usize;
        m["entries"][i]["sha256"] = sha256(&payload[offset..offset + bytes]).into();
    });
    rejected.push(k4);
    let k5 = copy("k5");
    remanifest(&k5, &|m, _| m["global_step"] = serde_json::json!(4.5));
    rejected.push(k5);
    let k6 = copy("k6");
    remanifest(&k6, &|m, _| m["schedule_sha256"] = "0".repeat(64).into());
    rejected.push(k6);
    let k7 = copy("k7");
    fs::remove_file(k7.join(COMMIT)).unwrap();
    rejected.push(k7);
    for (i, root) in rejected.iter().enumerate() {
        assert!(
            read_checkpoint(root, &toy.binding, &device).is_err(),
            "K{i} accepted"
        );
    }
    // Not one of K0-K7: the recorded backend/thread/RNG identity must also match.
    for (i, (key, value)) in [
        ("rng", json!("xorshift")),
        ("backend", json!("cuda")),
        ("threads", json!(2)),
    ]
    .into_iter()
    .enumerate()
    {
        let root = copy(&format!("identity{i}"));
        remanifest(&root, &|m, _| m[key] = value.clone());
        assert!(
            read_checkpoint(&root, &toy.binding, &device).is_err(),
            "{key} accepted"
        );
    }

    // Three writer stops: nothing before the commit marker is ever accepted.
    // The input is B's committed state, so no extra optimizer update is run.
    let four = read_checkpoint(&b, &toy.binding, &device).unwrap();
    for (i, stop) in [
        WriterStop::HalfPayload,
        WriterStop::AfterPayloadSync,
        WriterStop::AfterManifestSync,
    ]
    .into_iter()
    .enumerate()
    {
        let root = dir.join(format!("f{i}"));
        write(&root, &four, &toy.binding, Some(stop)).unwrap();
        assert!(!root.join(COMMIT).exists(), "F{i} committed");
        assert!(
            read_checkpoint(&root, &toy.binding, &device).is_err(),
            "F{i} accepted"
        );
    }
    assert!(
        write(&b, &four, &toy.binding, None).is_err(),
        "existing checkpoint replaced"
    );
    assert_eq!(dir_hashes(&b), committed, "valid checkpoint changed");
    assert!(read_checkpoint(&b, &toy.binding, &device).is_ok());
    fs::remove_dir_all(&dir).unwrap();
}
