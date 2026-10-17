//! Formal R2 (CARE fold0), Rust side. Reads the frozen fixture written by
//! tools/r2_formal.py and writes every update record for comparison there; it
//! never sees the Torch reference. Conditions:
//! examples/configs/rust-r2-formal-20261017.json.
//!
//! cases FIXTURE FIXTURE_SHA OUT             one_update, eight_updates, mature_import, floor_tie
//! resume-first FIXTURE FIXTURE_SHA CKPT     4 updates of eight_updates, then a checkpoint
//! resume-second FIXTURE FIXTURE_SHA CKPT OUT  restore in this process, then updates 5..8
use banto_ai::{
    Error, Result, SmallForecaster,
    synthetic_checkpoint::{self, Binding, TrainingState, sha256},
    training::{
        AdamW, AdamWState, Parameter, clip_global_norm, loss_and_gradients, pinball_loss, read,
    },
};
use burn::tensor::{Device, Tensor, TensorData};
use serde_json::{Value, json};
use std::{collections::BTreeMap, env, fs, io::Write, path::Path};

const UPDATES: usize = 8;

struct Fixture {
    values: BTreeMap<String, (Vec<usize>, Vec<f32>)>,
    meta: Value,
    sha: String,
    device: Device,
}
impl Fixture {
    /// Reads inputs.json (whose bytes must hash to `expected`) and inputs.f32,
    /// checking every entry's bounds, shape and hash before use.
    fn load(dir: &Path, expected: &str) -> Result<Self> {
        let meta_bytes = fs::read(dir.join("inputs.json"))?;
        if sha256(&meta_bytes) != expected {
            return Err(Error::Integrity("fixture manifest hash".into()));
        }
        let meta: Value = serde_json::from_slice(&meta_bytes)?;
        let raw = fs::read(dir.join("inputs.f32"))?;
        if meta["payload_sha256"] != sha256(&raw) {
            return Err(Error::Integrity("fixture payload hash".into()));
        }
        let mut values = BTreeMap::new();
        for e in meta["entries"].as_array().ok_or_else(|| bad("entries"))? {
            let (offset, bytes) = (int(&e["offset"])?, int(&e["bytes"])?);
            let shape: Vec<usize> = e["shape"]
                .as_array()
                .ok_or_else(|| bad("shape"))?
                .iter()
                .map(int)
                .collect::<Result<_>>()?;
            let end = offset.checked_add(bytes).ok_or_else(|| bad("overflow"))?;
            if end > raw.len() || bytes != shape.iter().product::<usize>() * 4 {
                return Err(bad("entry bounds or shape"));
            }
            let chunk = &raw[offset..end];
            if e["sha256"] != sha256(chunk) {
                return Err(Error::Integrity("fixture entry hash".into()));
            }
            let v = chunk
                .chunks_exact(4)
                .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
                .collect();
            let name = e["name"].as_str().ok_or_else(|| bad("name"))?.to_string();
            if values.insert(name, (shape, v)).is_some() {
                return Err(bad("duplicate entry"));
            }
        }
        Ok(Self {
            values,
            meta,
            sha: expected.into(),
            device: Device::flex(),
        })
    }
    fn get(&self, name: &str) -> Result<&(Vec<usize>, Vec<f32>)> {
        self.values
            .get(name)
            .ok_or_else(|| Error::Input(format!("fixture has no {name}")))
    }
    fn flat(&self, name: &str) -> Result<Tensor<1>> {
        let (_, v) = self.get(name)?;
        Ok(Tensor::from_data(
            TensorData::new(v.clone(), [v.len()]),
            &self.device,
        ))
    }
    fn names(&self) -> Result<Vec<String>> {
        self.meta["parameter_order"]
            .as_array()
            .ok_or_else(|| bad("parameter_order"))?
            .iter()
            .map(|n| n.as_str().map(String::from).ok_or_else(|| bad("name")))
            .collect()
    }
    fn parameters(&self) -> Result<Vec<Parameter>> {
        self.names()?
            .iter()
            .map(|n| {
                let (shape, v) = self.get(&format!("param/{n}"))?;
                Parameter::new(n, shape.clone(), v.clone(), &self.device)
            })
            .collect()
    }
    fn buffers(&self) -> Result<BTreeMap<String, Tensor<1>>> {
        ["scale_floor", "position", "time_mask"]
            .iter()
            .map(|n| Ok((n.to_string(), self.flat(&format!("buffer/{n}"))?)))
            .collect()
    }
    /// The saved step-4096 AdamW state; the step is an integer in the manifest.
    fn mature(&self) -> Result<AdamWState> {
        let names = self.names()?;
        Ok(AdamWState {
            step: self.meta["adamw_step"]
                .as_u64()
                .ok_or_else(|| bad("step"))?,
            m: names
                .iter()
                .map(|n| self.flat(&format!("adamw/m/{n}")))
                .collect::<Result<_>>()?,
            v: names
                .iter()
                .map(|n| self.flat(&format!("adamw/v/{n}")))
                .collect::<Result<_>>()?,
        })
    }
    fn batch(&self, label: &str) -> Result<(Tensor<3>, Tensor<3>)> {
        let tensor = |name: String| -> Result<Tensor<3>> {
            let (shape, v) = self.get(&name)?;
            let dims: [usize; 3] = shape.as_slice().try_into().map_err(|_| bad("batch rank"))?;
            Ok(Tensor::from_data(
                TensorData::new(v.clone(), dims),
                &self.device,
            ))
        };
        Ok((
            tensor(format!("{label}/context"))?,
            tensor(format!("{label}/actual"))?,
        ))
    }
    fn optimizer(&self) -> Result<(AdamW, f32)> {
        let r = &self.meta["recipe"];
        let f = |v: &Value| v.as_f64().ok_or_else(|| bad("recipe"));
        Ok((
            AdamW {
                lr: f(&r["lr"])?,
                betas: (f(&r["betas"][0])?, f(&r["betas"][1])?),
                eps: f(&r["eps"])?,
                weight_decay: f(&r["weight_decay"])?,
            },
            f(&r["clip_global_norm"])? as f32,
        ))
    }
    fn binding(&self) -> Result<Binding> {
        let parameters = self.parameters()?;
        let buffers = ["scale_floor", "position", "time_mask"]
            .iter()
            .map(|n| {
                let (shape, v) = self.get(&format!("buffer/{n}"))?;
                Ok((n.to_string(), shape.clone(), v.clone()))
            })
            .collect::<Result<_>>()?;
        Ok(Binding {
            parameter_order: parameters
                .iter()
                .map(|p| (p.name.clone(), p.shape.clone()))
                .collect(),
            buffers,
            schedule: (0..UPDATES).map(|k| format!("batch/{k}")).collect(),
            fixture_sha256: self.sha.clone(),
            recipe: self.meta["recipe"].clone(),
        })
    }
}
fn bad(what: &str) -> Error {
    Error::Input(format!("fixture {what}"))
}
fn int(v: &Value) -> Result<usize> {
    v.as_u64().map(|x| x as usize).ok_or_else(|| bad("integer"))
}

/// Named float32 records, written as one payload plus a layout.
#[derive(Default)]
struct Records {
    raw: Vec<u8>,
    entries: Vec<Value>,
}
impl Records {
    fn put<const D: usize>(&mut self, name: &str, t: &Tensor<D>) -> Result<()> {
        let v = read(t)?;
        let start = self.raw.len();
        for x in &v {
            self.raw.extend_from_slice(&x.to_le_bytes());
        }
        self.entries.push(
            json!({"name": name, "shape": t.dims().to_vec(), "offset": start,
            "bytes": self.raw.len() - start, "sha256": sha256(&self.raw[start..])}),
        );
        Ok(())
    }
    fn save(&self, dir: &Path, extra: Value) -> Result<()> {
        fs::create_dir(dir)?;
        write_new(&dir.join("records.f32"), &self.raw)?;
        let layout =
            json!({"entries": self.entries, "payload_sha256": sha256(&self.raw), "run": extra});
        write_new(
            &dir.join("records.json"),
            &serde_json::to_vec_pretty(&layout)?,
        )
    }
}
fn write_new(path: &Path, bytes: &[u8]) -> Result<()> {
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    f.write_all(bytes)?;
    f.sync_all()?;
    Ok(())
}

struct Run<'a> {
    fx: &'a Fixture,
    buffers: BTreeMap<String, Tensor<1>>,
    optimizer: AdamW,
    max_norm: f32,
    records: Records,
}
impl Run<'_> {
    /// The inference model on the given parameter tensors (leaves or plain).
    fn model(&self, parameters: &[Parameter], tensors: &[Tensor<1>]) -> Result<SmallForecaster> {
        let mut state = self.buffers.clone();
        for (p, t) in parameters.iter().zip(tensors) {
            state.insert(p.name.clone(), t.clone());
        }
        SmallForecaster::from_named(state)
    }
    /// Loss, raw and clipped gradients, norm and coefficient on one batch.
    fn gradients(
        &mut self,
        label: &str,
        parameters: &[Parameter],
        batch: &str,
    ) -> Result<Vec<Tensor<1>>> {
        let (context, actual) = self.fx.batch(batch)?;
        let (loss, raw) = loss_and_gradients(parameters, |leaves| {
            let f = self.model(parameters, leaves)?.forward(context)?;
            Ok(pinball_loss(f.normalized, actual, f.center, f.scale))
        })?;
        let clipped = clip_global_norm(raw.clone(), self.max_norm)?;
        self.records.put(&format!("{label}/loss"), &loss)?;
        self.records.put(&format!("{label}/norm"), &clipped.norm)?;
        self.records
            .put(&format!("{label}/coefficient"), &clipped.coefficient)?;
        for (p, (g, c)) in parameters.iter().zip(raw.iter().zip(&clipped.gradients)) {
            self.records.put(&format!("{label}/raw/{}", p.name), g)?;
            self.records
                .put(&format!("{label}/clipped/{}", p.name), c)?;
        }
        Ok(clipped.gradients)
    }
    /// One update on batch k, then the parameters, moments and the forward of
    /// the next batch (or of batch k after the last update).
    fn update(
        &mut self,
        label: &str,
        parameters: &mut [Parameter],
        state: &mut AdamWState,
        k: usize,
    ) -> Result<()> {
        let clipped = self.gradients(label, parameters, &format!("batch/{k}"))?;
        self.optimizer.step(parameters, &clipped, state)?;
        for (i, p) in parameters.iter().enumerate() {
            self.records
                .put(&format!("{label}/param/{}", p.name), &p.value)?;
            self.records
                .put(&format!("{label}/m/{}", p.name), &state.m[i])?;
            self.records
                .put(&format!("{label}/v/{}", p.name), &state.v[i])?;
        }
        let (context, _) = self
            .fx
            .batch(&format!("batch/{}", (k + 1).min(UPDATES - 1)))?;
        let plain: Vec<Tensor<1>> = parameters.iter().map(|p| p.value.clone()).collect();
        let f = self.model(parameters, &plain)?.forward(context)?;
        self.records.put(&format!("{label}/forward"), &f.normalized)
    }
}

fn run(args: &[String]) -> Result<()> {
    let usage =
        || Error::Input("usage: cases|resume-first|resume-second FIXTURE SHA DIR [OUT]".into());
    let (mode, dir) = (
        args.first().ok_or_else(usage)?,
        args.get(3).ok_or_else(usage)?,
    );
    let fx = Fixture::load(
        Path::new(args.get(1).ok_or_else(usage)?),
        args.get(2).ok_or_else(usage)?,
    )?;
    let (optimizer, max_norm) = fx.optimizer()?;
    let mut r = Run {
        buffers: fx.buffers()?,
        fx: &fx,
        optimizer,
        max_norm,
        records: Records::default(),
    };
    let steps = |s: &AdamWState| json!(s.step);
    match mode.as_str() {
        "cases" => {
            let mut p = fx.parameters()?;
            let mut s = AdamWState::zeros(&p);
            r.update("one_update/1", &mut p, &mut s, 0)?;
            let mut p = fx.parameters()?;
            let mut s8 = AdamWState::zeros(&p);
            for k in 0..UPDATES {
                r.update(&format!("eight_updates/{}", k + 1), &mut p, &mut s8, k)?;
            }
            let mut pm = fx.parameters()?;
            let mut sm = fx.mature()?;
            r.update("mature_import/1", &mut pm, &mut sm, 0)?;
            let p = fx.parameters()?;
            r.gradients("floor_tie", &p, "floor_tie")?;
            let extra = json!({"steps": {"one_update": steps(&s), "eight_updates": steps(&s8), "mature_import": steps(&sm)}});
            r.records.save(Path::new(dir), extra)
        }
        "resume-first" => {
            let mut p = fx.parameters()?;
            let mut s = AdamWState::zeros(&p);
            for k in 0..UPDATES / 2 {
                r.update(&format!("resume/{}", k + 1), &mut p, &mut s, k)?;
            }
            let state = TrainingState {
                parameters: p,
                optimizer: s,
                next_position: UPDATES / 2,
            };
            synthetic_checkpoint::write(Path::new(dir), &state, &fx.binding()?, None)
        }
        "resume-second" => {
            let out = args.get(4).ok_or_else(usage)?;
            let state =
                synthetic_checkpoint::read_checkpoint(Path::new(dir), &fx.binding()?, &fx.device)?;
            let (mut p, mut s) = (state.parameters, state.optimizer);
            for k in state.next_position..UPDATES {
                r.update(&format!("resume/{}", k + 1), &mut p, &mut s, k)?;
            }
            r.records.save(
                Path::new(out),
                json!({"steps": {"resume": steps(&s)}, "restored_position": state.next_position}),
            )
        }
        _ => Err(usage()),
    }
}

fn main() -> std::result::Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().skip(1).collect();
    run(&args)?;
    println!("{}", json!({"status": "complete", "mode": args[0]}));
    Ok(())
}
