//! `banto.synthetic-training-checkpoint.v1` for the R2P artificial training
//! state: named parameters, AdamW moments, an integer step and the schedule
//! position. A checkpoint is a fresh directory holding `payload.f32`
//! (little-endian float32), a deterministic `manifest.json`, and `COMMIT`,
//! created exclusively and last. Anything without a valid commit is never read
//! as state, and an existing directory is never replaced.

use crate::{
    Error, Result,
    training::{AdamWState, Parameter, read},
};
use burn::tensor::{Device, Tensor, TensorData};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeSet,
    fs::{self, File, OpenOptions},
    io::Write,
    path::Path,
};

pub const SCHEMA: &str = "banto.synthetic-training-checkpoint.v1";
pub const PAYLOAD: &str = "payload.f32";
pub const MANIFEST: &str = "manifest.json";
pub const COMMIT: &str = "COMMIT";
pub const BACKEND: &str = "burn 0.22.0 flex cpu float32";
pub const THREADS: u64 = 1;
pub const RNG: &str = "none";

pub fn sha256(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

/// Identity that a checkpoint must carry and that a restore must match.
#[derive(Clone, Debug)]
pub struct Binding {
    pub parameter_order: Vec<(String, Vec<usize>)>,
    /// Fixed non-trainable tensors (name, shape, values), saved and checked.
    pub buffers: Vec<(String, Vec<usize>, Vec<f32>)>,
    pub schedule: Vec<String>,
    pub fixture_sha256: String,
    pub recipe: Value,
}
impl Binding {
    pub fn schedule_sha256(&self) -> String {
        sha256(serde_json::to_string(&self.schedule).unwrap().as_bytes())
    }
}

/// Training state at an update boundary: `next_position` indexes the schedule.
pub struct TrainingState {
    pub parameters: Vec<Parameter>,
    pub optimizer: AdamWState,
    pub next_position: usize,
}

/// Where a writer may be stopped to check that partial output is never read.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WriterStop {
    HalfPayload,
    AfterPayloadSync,
    AfterManifestSync,
}

fn sync_dir(dir: &Path) -> Result<()> {
    File::open(dir)?.sync_all()?;
    Ok(())
}
fn write_new(path: &Path, bytes: &[u8]) -> Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    f.write_all(bytes)?;
    f.sync_all()?;
    Ok(())
}

/// Deterministic manifest for a state; the payload is returned alongside.
pub fn encode(state: &TrainingState, binding: &Binding) -> Result<(Vec<u8>, Value)> {
    check_order(&state.parameters, binding)?;
    let n = state.parameters.len();
    if state.optimizer.m.len() != n || state.optimizer.v.len() != n {
        return Err(Error::Input("moments do not match parameters".into()));
    }
    let mut payload = Vec::new();
    let mut entries = Vec::new();
    let roles = [
        ("parameter", None),
        ("moment1", Some(&state.optimizer.m)),
        ("moment2", Some(&state.optimizer.v)),
    ];
    for (role, tensors) in roles {
        for (i, p) in state.parameters.iter().enumerate() {
            let values = match tensors {
                None => read(&p.value)?,
                Some(t) => read(&t[i])?,
            };
            let bytes: Vec<u8> = values.iter().flat_map(|v| v.to_le_bytes()).collect();
            entries.push(json!({
                "name": p.name, "role": role, "shape": p.shape, "dtype": "float32-le",
                "offset": payload.len(), "bytes": bytes.len(), "sha256": sha256(&bytes),
            }));
            payload.extend(bytes);
        }
    }
    for (name, shape, values) in &binding.buffers {
        let bytes: Vec<u8> = values.iter().flat_map(|v| v.to_le_bytes()).collect();
        entries.push(json!({
            "name": name, "role": "buffer", "shape": shape, "dtype": "float32-le",
            "offset": payload.len(), "bytes": bytes.len(), "sha256": sha256(&bytes),
        }));
        payload.extend(bytes);
    }
    let step = state.optimizer.step;
    let manifest = json!({
        "schema": SCHEMA,
        "entries": entries,
        "payload_bytes": payload.len(),
        "payload_sha256": sha256(&payload),
        "global_step": step,
        "per_parameter_steps": vec![step; state.parameters.len()],
        "next_position": state.next_position,
        "schedule": binding.schedule,
        "schedule_sha256": binding.schedule_sha256(),
        "fixture_sha256": binding.fixture_sha256,
        "recipe": binding.recipe,
        "backend": BACKEND,
        "threads": THREADS,
        "rng": RNG,
    });
    Ok((payload, manifest))
}

/// Writes a new checkpoint directory: payload, then manifest, each synced and
/// read back to confirm the bytes, then the commit marker last. `stop` ends the
/// writer early.
pub fn write(
    root: &Path,
    state: &TrainingState,
    binding: &Binding,
    stop: Option<WriterStop>,
) -> Result<()> {
    let (payload, manifest) = encode(state, binding)?;
    let manifest = serde_json::to_vec_pretty(&manifest)?;
    fs::create_dir(root)?;
    if stop == Some(WriterStop::HalfPayload) {
        return write_new(&root.join(PAYLOAD), &payload[..payload.len() / 2]);
    }
    write_new(&root.join(PAYLOAD), &payload)?;
    sync_dir(root)?;
    if stop == Some(WriterStop::AfterPayloadSync) {
        return Ok(());
    }
    write_new(&root.join(MANIFEST), &manifest)?;
    sync_dir(root)?;
    if stop == Some(WriterStop::AfterManifestSync) {
        return Ok(());
    }
    if fs::read(root.join(PAYLOAD))? != payload || fs::read(root.join(MANIFEST))? != manifest {
        return Err(Error::Integrity(
            "written checkpoint differs from its bytes".into(),
        ));
    }
    commit(root, &manifest)?;
    match root.parent() {
        Some(parent) if !parent.as_os_str().is_empty() => sync_dir(parent),
        _ => Ok(()),
    }
}

/// The exclusive commit marker binds the exact manifest bytes.
pub fn commit(root: &Path, manifest: &[u8]) -> Result<()> {
    let marker = json!({"schema": SCHEMA, "manifest_sha256": sha256(manifest)});
    write_new(&root.join(COMMIT), &serde_json::to_vec(&marker)?)?;
    sync_dir(root)
}

fn check_order(parameters: &[Parameter], binding: &Binding) -> Result<()> {
    let names: Vec<(String, Vec<usize>)> = parameters
        .iter()
        .map(|p| (p.name.clone(), p.shape.clone()))
        .collect();
    match names == binding.parameter_order {
        true => Ok(()),
        false => Err(Error::Integrity(
            "parameters differ from the bound order".into(),
        )),
    }
}
fn bad(reason: impl Into<String>) -> Error {
    Error::Integrity(reason.into())
}
fn integer(manifest: &Value, key: &str) -> Result<u64> {
    manifest[key]
        .as_u64()
        .ok_or_else(|| bad(format!("{key} is not a nonnegative integer")))
}

/// Restores a committed checkpoint after checking the marker, hashes, schema,
/// the complete and unique entry set, shapes, finite values, nonnegative second
/// moments, integer steps and the bound schedule/fixture/recipe. Only then are
/// tensors created; there is no fallback to a fresh state.
pub fn read_checkpoint(root: &Path, binding: &Binding, device: &Device) -> Result<TrainingState> {
    let marker_bytes = fs::read(root.join(COMMIT)).map_err(|_| bad("missing commit marker"))?;
    let marker: Value = serde_json::from_slice(&marker_bytes)?;
    let manifest_bytes = fs::read(root.join(MANIFEST)).map_err(|_| bad("missing manifest"))?;
    if marker["schema"] != SCHEMA || marker["manifest_sha256"] != sha256(&manifest_bytes) {
        return Err(bad("commit marker does not bind this manifest"));
    }
    let manifest: Value = serde_json::from_slice(&manifest_bytes)?;
    if manifest["schema"] != SCHEMA {
        return Err(bad("unknown schema"));
    }
    let payload = fs::read(root.join(PAYLOAD)).map_err(|_| bad("missing payload"))?;
    if integer(&manifest, "payload_bytes")? != payload.len() as u64
        || manifest["payload_sha256"] != sha256(&payload)
    {
        return Err(bad("payload size or hash mismatch"));
    }
    if manifest["schedule"] != json!(binding.schedule)
        || manifest["schedule_sha256"] != binding.schedule_sha256()
        || manifest["fixture_sha256"] != binding.fixture_sha256
        || manifest["recipe"] != binding.recipe
    {
        return Err(bad("schedule, fixture or recipe binding mismatch"));
    }
    if manifest["backend"] != BACKEND || manifest["threads"] != THREADS || manifest["rng"] != RNG {
        return Err(bad("backend, thread or RNG identity mismatch"));
    }
    let step = integer(&manifest, "global_step")?;
    let next_position = integer(&manifest, "next_position")? as usize;
    let per = manifest["per_parameter_steps"]
        .as_array()
        .ok_or_else(|| bad("missing per-parameter steps"))?;
    if per.len() != binding.parameter_order.len() || per.iter().any(|s| s.as_u64() != Some(step)) {
        return Err(bad("per-parameter steps differ from the global step"));
    }
    if next_position > binding.schedule.len() || next_position as u64 != step {
        return Err(bad("schedule position does not match the step"));
    }

    let entries = manifest["entries"]
        .as_array()
        .ok_or_else(|| bad("missing entries"))?;
    let mut seen = BTreeSet::new();
    for e in entries {
        let key = (
            e["role"].as_str().unwrap_or(""),
            e["name"].as_str().unwrap_or(""),
        );
        if !seen.insert(key) {
            return Err(bad(format!("duplicate entry {key:?}")));
        }
    }
    let roles = ["parameter", "moment1", "moment2"];
    if entries.len() != roles.len() * binding.parameter_order.len() + binding.buffers.len() {
        return Err(bad("entry set is incomplete or has extra entries"));
    }
    let mut tensors: Vec<Vec<Tensor<1>>> = vec![Vec::new(); roles.len()];
    let mut parameters = Vec::new();
    for (r, role) in roles.iter().enumerate() {
        for (name, shape) in &binding.parameter_order {
            let e = entries
                .iter()
                .find(|e| e["role"] == *role && e["name"] == *name)
                .ok_or_else(|| bad(format!("missing {role} {name}")))?;
            let expected_shape: Vec<Value> = shape.iter().map(|d| json!(d)).collect();
            if e["shape"] != json!(expected_shape) || e["dtype"] != "float32-le" {
                return Err(bad(format!("{role} {name} shape or dtype mismatch")));
            }
            let (offset, bytes) = (
                integer(e, "offset")? as usize,
                integer(e, "bytes")? as usize,
            );
            let len: usize = shape.iter().product();
            if bytes != len * 4
                || offset
                    .checked_add(bytes)
                    .is_none_or(|end| end > payload.len())
            {
                return Err(bad(format!("{role} {name} is out of bounds")));
            }
            let chunk = &payload[offset..offset + bytes];
            if e["sha256"] != sha256(chunk) {
                return Err(bad(format!("{role} {name} hash mismatch")));
            }
            let values: Vec<f32> = chunk
                .chunks_exact(4)
                .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
                .collect();
            if values.iter().any(|v| !v.is_finite()) {
                return Err(bad(format!("{role} {name} is not finite")));
            }
            if *role == "moment2" && values.iter().any(|v| *v < 0.0) {
                return Err(bad(format!("negative second moment {name}")));
            }
            if *role == "parameter" {
                parameters.push(Parameter::new(name, shape.clone(), values, device)?);
            } else {
                tensors[r].push(Tensor::from_data(TensorData::new(values, [len]), device));
            }
        }
    }
    for (name, shape, values) in &binding.buffers {
        let e = entries
            .iter()
            .find(|e| e["role"] == "buffer" && e["name"] == *name)
            .ok_or_else(|| bad(format!("missing buffer {name}")))?;
        let bytes: Vec<u8> = values.iter().flat_map(|v| v.to_le_bytes()).collect();
        let (offset, len) = (
            integer(e, "offset")? as usize,
            integer(e, "bytes")? as usize,
        );
        let saved = offset
            .checked_add(len)
            .and_then(|end| payload.get(offset..end));
        if e["shape"] != json!(shape)
            || e["dtype"] != "float32-le"
            || saved != Some(bytes.as_slice())
        {
            return Err(bad(format!("buffer {name} differs from the bound value")));
        }
    }
    let v = tensors.pop().unwrap();
    let m = tensors.pop().unwrap();
    Ok(TrainingState {
        parameters,
        optimizer: AdamWState { step, m, v },
        next_position,
    })
}
