//! Same-input norm/attention kernel diagnosis from pinned saved tensors.
use banto_ai::checkpoint::sha256;
use burn::tensor::{Bool, Device, Tensor, TensorData, activation};
use serde::Deserialize;
use serde_json::json;
use std::{collections::BTreeMap, env, fs, io::Write, path::Path};
#[derive(Deserialize)]
struct Entry {
    shape: Vec<usize>,
    offset_bytes: usize,
    length_bytes: usize,
}
#[derive(Deserialize)]
struct Manifest {
    schema: String,
    payload_sha256: String,
    tensors: BTreeMap<String, Entry>,
}
struct Inputs {
    m: Manifest,
    raw: Vec<u8>,
    device: Device,
}
impl Inputs {
    fn p<const D: usize>(&self, name: &str, shape: [usize; D]) -> Tensor<D> {
        let e = &self.m.tensors[name];
        assert_eq!(
            e.shape.iter().product::<usize>(),
            shape.iter().product::<usize>()
        );
        let end = e.offset_bytes.checked_add(e.length_bytes).unwrap();
        assert!(end <= self.raw.len());
        let v: Vec<f32> = self.raw[e.offset_bytes..end]
            .chunks_exact(4)
            .map(|v| f32::from_le_bytes(v.try_into().unwrap()))
            .collect();
        assert_eq!(v.len() * 4, e.length_bytes);
        Tensor::from_data(TensorData::new(v, shape), &self.device)
    }
    fn linear<const D: usize>(&self, x: Tensor<D>, name: &str) -> Tensor<D> {
        let mut shape = x.dims();
        let width = shape[D - 1];
        let rows = shape.iter().product::<usize>() / width;
        let out = self.m.tensors[&format!("{name}.weight")].shape[0];
        let w = self.p(&format!("{name}.weight"), [out, width]).transpose();
        let b = self.p(&format!("{name}.bias"), [1, out]);
        shape[D - 1] = out;
        (x.reshape([rows, width]).matmul(w) + b).reshape(shape)
    }
}
struct Outputs {
    raw: Vec<u8>,
    entries: BTreeMap<String, serde_json::Value>,
}
impl Outputs {
    fn put<const D: usize>(&mut self, name: String, t: Tensor<D>) {
        let start = self.raw.len();
        let shape = t.dims();
        let v = t.to_data().to_vec::<f32>().unwrap();
        assert!(
            v.iter()
                .all(|x| x.is_finite() || (name.ends_with(".logits") && *x == f32::NEG_INFINITY))
        );
        for x in v {
            self.raw.extend_from_slice(&x.to_le_bytes());
        }
        self.entries.insert(
            name,
            json!({"shape":shape.to_vec(),"offset_bytes":start,"length_bytes":self.raw.len()-start}),
        );
    }
}
fn mean(x: Tensor<2>) -> Tensor<2> {
    let [rows, width] = x.dims();
    let mut n = width;
    let mut x = x;
    while n > 1 {
        x = x
            .reshape([rows, n / 2, 2])
            .sum_dim(2)
            .reshape([rows, n / 2]);
        n /= 2;
    }
    x / width as f32
}
fn write(p: &Path, v: &[u8]) {
    fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(p)
        .unwrap()
        .write_all(v)
        .unwrap();
}
fn main() {
    let a: Vec<String> = env::args().skip(1).collect();
    assert_eq!(a.len(), 4, "MANIFEST INPUT TRUSTED_SHA NEW_OUTPUT");
    let m = fs::read(&a[0]).unwrap();
    let raw = fs::read(&a[1]).unwrap();
    assert!(m.len() < 256 * 1024 && raw.len() < 32 * 1024 * 1024);
    assert_eq!(sha256(&m), a[2]);
    let m: Manifest = serde_json::from_slice(&m).unwrap();
    assert_eq!(m.schema, "banto.r1-upstream-diagnosis.v1");
    assert_eq!(sha256(&raw), m.payload_sha256);
    let data = Inputs {
        m,
        raw,
        device: Device::flex(),
    };
    let mut out = Outputs {
        raw: vec![],
        entries: BTreeMap::new(),
    };
    for side in ["python", "rust"] {
        for j in 0..3 {
            let key = format!("{side}.norm{j}");
            let x = data.p(&format!("{key}.input"), [120, 64]);
            let mu = mean(x.clone());
            let centered = x - mu.clone();
            let var = mean(centered.clone().square());
            let sqrt = (var + 1e-5).sqrt();
            let inv = sqrt.clone().recip();
            let w = data.p(&format!("blocks.1.norms.{j}.weight"), [1, 64]);
            let b = data.p(&format!("blocks.1.norms.{j}.bias"), [1, 64]);
            let division = centered.clone() / sqrt * w.clone() + b.clone();
            let reciprocal = centered * inv.clone() * w + b;
            out.put(format!("{key}.mean"), mu);
            out.put(format!("{key}.inverse_std"), inv);
            out.put(format!("{key}.division"), division);
            out.put(format!("{key}.reciprocal"), reciprocal);
        }
        for kind in ["temporal", "variate"] {
            let (batch, n) = if kind == "temporal" { (24, 5) } else { (40, 3) };
            let key = format!("{side}.{kind}");
            let name = format!("blocks.1.{kind}");
            let x = data.p(&format!("{key}.input"), [batch, n, 64]);
            let project = |s: &str| {
                data.linear(x.clone(), &format!("{name}.{s}"))
                    .reshape([batch, n, 4, 16])
                    .swap_dims(1, 2)
            };
            let q = project("q");
            let k = project("k");
            let v = project("v");
            let mut logits = q.clone().matmul(k.clone().swap_dims(2, 3)) / 4.;
            if kind == "temporal" {
                let mask: Vec<bool> = (0..n * n).map(|i| i % n > i / n).collect();
                logits = logits.mask_fill(
                    Tensor::<4, Bool>::from_data(TensorData::new(mask, [1, 1, n, n]), &data.device),
                    f32::NEG_INFINITY,
                );
            }
            let probs = activation::softmax(logits.clone(), 3);
            let mixed = probs
                .clone()
                .matmul(v.clone())
                .swap_dims(1, 2)
                .reshape([batch, n, 64]);
            let y = data.linear(mixed.clone(), &format!("{name}.out"));
            out.put(format!("{key}.q"), q);
            out.put(format!("{key}.k"), k);
            out.put(format!("{key}.v"), v);
            out.put(format!("{key}.logits"), logits);
            out.put(format!("{key}.probs"), probs);
            out.put(format!("{key}.mixed"), mixed);
            out.put(format!("{key}.reference"), y);
        }
    }
    let p = Path::new(&a[3]);
    fs::create_dir(p).unwrap();
    assert!(out.raw.len() < 32 * 1024 * 1024);
    write(&p.join("tensors.bin"), &out.raw);
    let m=serde_json::to_vec(&json!({"tensors":out.entries,"payload_sha256":sha256(&out.raw),"fixture_manifest_sha256":a[2]})).unwrap();
    write(&p.join("manifest.json"), &m);
    let s = serde_json::to_vec(
        &json!({"training":false,"full_forward_calls":0,"norm_inputs":6,"attention_inputs":4}),
    )
    .unwrap();
    write(&p.join("summary.json"), &s);
    write(&p.join("root-closed.json"),&serde_json::to_vec(&json!({"status":"complete","files":[{"name":"tensors.bin","bytes":out.raw.len(),"sha256":sha256(&out.raw)},{"name":"manifest.json","bytes":m.len(),"sha256":sha256(&m)},{"name":"summary.json","bytes":s.len(),"sha256":sha256(&s)}]})).unwrap());
    println!(
        "{}",
        json!({"status":"complete","norm_inputs":6,"attention_inputs":4})
    );
}
